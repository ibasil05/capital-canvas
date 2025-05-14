import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { createExportProgressWebSocket } from '@/lib/ws';
import { HeatmapChart } from '@/components/HeatmapChart';
import api from '@/lib/api';

// Define types for the model data
interface CompanyProfile {
  symbol: string;
  companyName: string;
  exchange: string;
  industry: string;
  sector: string;
  description: string;
  mktCap?: number;
  fullTimeEmployees?: string;
  website?: string;
}

// Define the form schema with Zod
const assumptionsSchema = z.object({
  revenue_growth: z.coerce.number().min(-100).max(100),
  ebitda_margin: z.coerce.number().min(-100).max(100),
  tax_rate: z.coerce.number().min(0).max(100),
  capex_percent: z.coerce.number().min(0).max(100),
  working_capital_percent: z.coerce.number().min(-100).max(100),
  terminal_growth: z.coerce.number().min(-10).max(10),
  discount_rate: z.coerce.number().min(1).max(50),
  debt_ratio: z.coerce.number().min(0).max(100),
  ev_to_ebitda_multiple: z.coerce.number().min(0.1),
  lbo_exit_multiple: z.coerce.number().min(0.1),
  lbo_years: z.coerce.number().int().min(1),
  debt_to_ebitda: z.coerce.number().min(0),
});

type AssumptionsFormValues = z.infer<typeof assumptionsSchema>;

export default function Model() {
  const { symbol } = useParams<{ symbol: string }>();
  
  const [activeTab, setActiveTab] = useState('assumptions');
  const [exportProgress, setExportProgress] = useState(0);
  const [exportType, setExportType] = useState<string | null>(null);
  const [modelId, setModelId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  
  // Query for model results
  const { data: modelResults, isLoading: isLoadingModelResults, error: modelResultsError } = useQuery({
    queryKey: ['modelResults', modelId],
    queryFn: async () => {
      console.log(`[Query modelResults] Attempting fetch. modelId: ${modelId}`);
      if (typeof modelId !== 'string' || !modelId) { 
        console.warn('[Query modelResults] Skipping fetch: modelId is not a valid string:', modelId);
        return null;
      }
      try {
        const response = await api.get(`/api/models/${modelId}`);
        console.log('[Query modelResults] Raw API Response:', response);
        console.log('[Query modelResults] Response Data (modelResults candidate):', response.data);
        if (!response.data || !response.data.valuation) {
          console.warn('[Query modelResults] Fetched data is missing or does not have a valuation property:', response.data);
        }
        return response.data;
      } catch (err) {
        console.error('[Query modelResults] Error fetching model results:', err);
        throw err;
      }
    },
    enabled: !!modelId,
    retry: 1,
  });

  useEffect(() => {
    console.log('[useEffect modelResults] modelResults state changed:', modelResults);
    if (modelResultsError) {
      console.error('[useEffect modelResults] Error state from query:', modelResultsError);
    }
  }, [modelResults, modelResultsError]);

  const { data: companyProfile, isLoading: isLoadingProfile, error: profileError } = useQuery<CompanyProfile, Error>({
    queryKey: ['companyProfile', symbol],
    queryFn: async () => {
      console.log(`Attempting to fetch company profile for symbol: '${symbol}'`);
      if (!symbol) {
        console.error("Symbol is undefined. Cannot fetch company profile.");
        throw new Error("Symbol is undefined, cannot fetch profile.");
      }
      try {
        const response = await api.get<CompanyProfile>(`/api/company/${symbol}`);
        console.log(`Raw API response for /api/company/${symbol}:`, response);
        if (!response.data || Object.keys(response.data).length === 0) {
            console.warn(`API for symbol '${symbol}' returned empty data object.`);
        }
        return response.data;
      } catch (err) {
        console.error(`Error fetching company profile for symbol '${symbol}':`, err);
        throw err; // Re-throw to let React Query handle it as an error state
      }
    },
    enabled: !!symbol, // Only run the query if the symbol exists
    retry: 1, // Optionally retry once on failure
  });

  const { data: defaultConfig } = useQuery<any>({ 
    queryKey: ['defaultConfig'],
    queryFn: async () => {
      const response = await api.get('/api/config/defaults');
      return response.data;
    },
  });
  
  const form = useForm<AssumptionsFormValues>({
    resolver: zodResolver(assumptionsSchema),
    defaultValues: {
      revenue_growth: 5,
      ebitda_margin: 20,
      tax_rate: 25,
      capex_percent: 5,
      working_capital_percent: 2,
      terminal_growth: 2,
      discount_rate: 10,
      debt_ratio: 30,
      ev_to_ebitda_multiple: 8,
      lbo_exit_multiple: 8,
      lbo_years: 5,
      debt_to_ebitda: 3,
    },
    mode: 'onBlur',
  });

  const getSafeNumberPercent = (path: string[], obj: any, fallback: number = 0): number => {
    let current = obj;
    for (const key of path) {
      if (typeof current !== 'object' || current === null || !(key in current)) {
        return fallback;
      }
      current = current[key];
    }
    if (typeof current === 'number') {
      return parseFloat((current * 100).toFixed(2)); 
    }
    return fallback;
  };
  
  useEffect(() => {
    if (defaultConfig?.default_assumptions) {
      const backendDefaults = defaultConfig.default_assumptions;
      form.reset({ 
        revenue_growth: getSafeNumberPercent(['revenue_growth', 'moderate_growth'], backendDefaults, 5),
        ebitda_margin: getSafeNumberPercent(['margins', 'ebitda_margin', 'stable'], backendDefaults, 20),
        tax_rate: getSafeNumberPercent(['tax_rate', 'effective_federal_state'], backendDefaults, 25),
        capex_percent: getSafeNumberPercent(['capex', 'capex_as_percent_of_revenue', 'maintainance'], backendDefaults, 5),
        working_capital_percent: getSafeNumberPercent(['working_capital', 'cash_as_percent_of_revenue'], backendDefaults, 2),
        terminal_growth: getSafeNumberPercent(['terminal_growth_rate', 'long_term_gdp_growth'], backendDefaults, 2),
        discount_rate: getSafeNumberPercent(['discount_rate', 'wacc', 'base_case'], backendDefaults, 10),
        debt_ratio: getSafeNumberPercent(['capital_structure', 'target_debt_to_total_capital'], backendDefaults, 30),
        ev_to_ebitda_multiple: getSafeNumberPercent(['trading_multiples', 'ev_to_ebitda', 'median'], backendDefaults, 8),
        lbo_exit_multiple: getSafeNumberPercent(['lbo', 'exit_multiple'], backendDefaults, 8),
        lbo_years: getSafeNumberPercent(['lbo', 'holding_period_years'], backendDefaults, 5),
        debt_to_ebitda: getSafeNumberPercent(['lbo', 'debt_to_ebitda', 'initial'], backendDefaults, 3),
      });
    }
  }, [defaultConfig, form]); 

  useEffect(() => {
    if (!isLoadingProfile) {
      if (companyProfile) {
        console.log('Company Profile Data (useEffect):', JSON.stringify(companyProfile, null, 2));
      } else if (profileError) {
        console.error('Company Profile Error (useEffect):', profileError.message);
      } else if (symbol) {
        console.log(`Company Profile Data for '${symbol}' (useEffect): No data and no error, check API response.`);
      }
    }
  }, [companyProfile, isLoadingProfile, profileError, symbol]);

  const onSubmit = async (data: AssumptionsFormValues) => {
    try {
      const numProjectionPeriods = 6;
      
      // Convert percentages to decimals
      const baseRevenueGrowth = data.revenue_growth / 100.0;
      const baseEbitdaMargin = data.ebitda_margin / 100.0;
      const baseGrossMargin = 0.55; // Default gross margin
      
      // Create arrays for forecast periods
      const revenueGrowthRates = Array(numProjectionPeriods).fill(baseRevenueGrowth);
      const ebitdaMargins = Array(numProjectionPeriods).fill(baseEbitdaMargin);
      const grossMargins = Array(numProjectionPeriods).fill(baseGrossMargin);
      
      // Get working capital assumptions from config or use defaults
      const receivableDays = defaultConfig?.default_assumptions?.working_capital?.receivables_days ?? 45;
      const inventoryDays = defaultConfig?.default_assumptions?.working_capital?.inventory_days ?? 60;
      const payableDays = defaultConfig?.default_assumptions?.working_capital?.payable_days ?? 30;
      
      // Get valuation assumptions from config or use defaults
      const evToEbitdaMultiple = defaultConfig?.default_assumptions?.trading_multiples?.ev_to_ebitda?.median ?? 8.0;
      const lboExitMultiple = defaultConfig?.default_assumptions?.lbo?.exit_multiple ?? 8.0;
      const lboYears = defaultConfig?.default_assumptions?.lbo?.holding_period_years ?? 5;
      const debtToEbitda = defaultConfig?.default_assumptions?.lbo?.debt_to_ebitda?.initial ?? 3.0;
      
      const backendAssumptions = {
        revenue_growth_rates: revenueGrowthRates,
        terminal_growth_rate: data.terminal_growth / 100.0,
        gross_margins: grossMargins,
        ebitda_margins: ebitdaMargins,
        
        receivable_days: receivableDays,
        inventory_days: inventoryDays,
        payable_days: payableDays,
        
        capex_percent_revenue: data.capex_percent / 100.0,
        discount_rate: data.discount_rate / 100.0,
        tax_rate: data.tax_rate / 100.0,
        
        ev_to_ebitda_multiple: data.ev_to_ebitda_multiple,
        lbo_exit_multiple: data.lbo_exit_multiple,
        lbo_years: data.lbo_years,
        debt_to_ebitda: data.debt_to_ebitda,
        
        // Fixed assets to revenue multiple (for balance sheet projections)
        base_fixed_assets_revenue_multiple: 0.70, // Default to 70% of revenue
        
        custom_assumptions: {}
      };

      console.log('Sending model request with assumptions:', backendAssumptions);
      
      const response = await api.post('/api/models', {
        ticker: symbol,
        assumptions: backendAssumptions,
      });
      
      console.log('Model created successfully:', response.data);
      setModelId(response.data.model_id);
      // Force React-Query to refetch the results for the new model ID
      queryClient.invalidateQueries({ queryKey: ['modelResults'] });
      setActiveTab('results');
    } catch (error: any) {
      console.error('Error creating model:', error.response?.data || error.message);
    }
  };

  const handleExport = async (type: 'Excel' | 'PPT') => {
    if (!modelId) {
      console.error('Model ID is not set. Cannot export.');
      alert('Please create a model first by submitting the assumptions form.');
      setActiveTab('assumptions');
      return;
    }
    try {
      const endpoint = type === 'Excel'
        ? `/api/export/${modelId}/excel`
        : `/api/export/${modelId}/ppt`;

      const resp = await api.get(endpoint, { responseType: 'blob' });
      const blob = new Blob([resp.data], { type: type === 'Excel' ?
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        : 'application/vnd.openxmlformats-officedocument.presentationml.presentation' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${symbol || 'model'}.${type === 'Excel' ? 'xlsx' : 'pptx'}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      return;
    } catch (error) {
      console.error('Error initiating export:', error);
      // Optionally, show a user-friendly error message
      setExportType(null); 
    }
  };

  if (!symbol) {
    return <div className="container mx-auto p-4 text-red-500">Error: No stock symbol provided in the URL.</div>;
  }

  if (isLoadingProfile) {
    return <div className="container mx-auto p-4">Loading company profile for {symbol}...</div>;
  }

  if (profileError) {
    return <div className="container mx-auto p-4 text-red-500">Error loading company profile for {symbol}: {profileError.message}. Please check the console.</div>;
  }
  
  if (!companyProfile || Object.keys(companyProfile).length === 0) {
    return <div className="container mx-auto p-4 text-orange-500">No company profile data was found for {symbol}. The API might have returned an empty response. Please check the console.</div>;
  }

  return (
    <div className="container mx-auto p-4">
      {/* The line above this comment is <div className...>, the line below is {companyProfile && ...}
         This ensures no stray {exportProgress} or similar is between them. */}
      {companyProfile && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>
              {companyProfile.companyName}
              {companyProfile.symbol && 
                ` (${companyProfile.symbol}${companyProfile.exchange ? ` | ${companyProfile.exchange}` : ''})`}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-neutral-600">{companyProfile.description || "No description available."}</p>
          </CardContent>
        </Card>
      )}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="assumptions">Assumptions</TabsTrigger>
          <TabsTrigger value="results" disabled={!modelId}>Results</TabsTrigger>
          <TabsTrigger value="heatmap" disabled={!modelId}>Heatmap</TabsTrigger>
          <TabsTrigger value="export" disabled={!modelId}>Export</TabsTrigger>
        </TabsList>
        
        <TabsContent value="assumptions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Financial Assumptions</CardTitle>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <FormField
                      control={form.control}
                      name="revenue_growth"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Revenue Growth (%)</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="e.g. 5 for 5%" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="ebitda_margin"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>EBITDA Margin (%)</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="e.g. 20 for 20%" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="tax_rate"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Tax Rate (%)</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="e.g. 25 for 25%" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="capex_percent"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>CapEx (% of Revenue)</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="e.g. 5 for 5%" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="working_capital_percent"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Working Capital (% of Revenue)</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="e.g. 2 for 2%" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="terminal_growth"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Terminal Growth Rate (%)</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="e.g. 2 for 2%" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="discount_rate"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Discount Rate (%)</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="e.g. 10 for 10%" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="debt_ratio"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Debt Ratio (%)</FormLabel>
                          <FormControl>
                            <Input 
                              type="number" 
                              placeholder="e.g. 30 for 30%" 
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="ev_to_ebitda_multiple"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>EV/EBITDA Multiple (x)</FormLabel>
                          <FormControl>
                            <Input type="number" placeholder="e.g. 8" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="lbo_exit_multiple"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>LBO Exit Multiple (x)</FormLabel>
                          <FormControl>
                            <Input type="number" placeholder="e.g. 8" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="lbo_years"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>LBO Holding Period (yrs)</FormLabel>
                          <FormControl>
                            <Input type="number" placeholder="e.g. 5" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="debt_to_ebitda"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Debt / EBITDA (x)</FormLabel>
                          <FormControl>
                            <Input type="number" placeholder="e.g. 3" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  <Button type="submit" disabled={form.formState.isSubmitting || !!exportType}>
                    {form.formState.isSubmitting ? "Creating Model..." : (modelId ? "Update Model" : "Create Model")}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="results" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Valuation Results</CardTitle>
            </CardHeader>
            <CardContent>
              {modelId && modelResults && modelResults.valuation ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <h3 className="text-sm text-neutral-500">DCF Enterprise Value</h3>
                    <p className="text-2xl font-semibold">
                      ${(modelResults.valuation.dcf_enterprise_value / 1e6 || 0).toFixed(1)}M
                    </p>
                  </div>
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <h3 className="text-sm text-neutral-500">DCF Equity Value</h3>
                    <p className="text-2xl font-semibold">
                      ${(modelResults.valuation.dcf_equity_value / 1e6 || 0).toFixed(1)}M
                    </p>
                  </div>
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <h3 className="text-sm text-neutral-500">DCF Implied Share Price</h3>
                    <p className="text-2xl font-semibold">
                      ${(modelResults.valuation.dcf_implied_share_price || 0).toFixed(2)}
                    </p>
                  </div>
                  {/* Implied Multiple - Placeholder: Needs clarification on which multiple to use */}
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <h3 className="text-sm text-neutral-500">Implied EV/EBITDA (DCF)</h3>
                    {/* This assumes you have a way to calculate or retrieve relevant EBITDA for the multiple */}
                    {/* For now, let's imagine it might be part of dcf_valuation or needs calculation */}
                    <p className="text-2xl font-semibold">
                      {(modelResults.valuation.dcf_implied_ev_ebitda_multiple || 'N/A')}
                      {typeof modelResults.valuation.dcf_implied_ev_ebitda_multiple === 'number' ? 'x' : ''}
                    </p>
                  </div>
                  {/* Upside - Placeholder: Needs current market price and clear target */}
                  <div className="p-4 bg-neutral-50 rounded-lg">
                    <h3 className="text-sm text-neutral-500">Upside (DCF vs Consensus)</h3>
                    {modelResults.valuation.consensus_target_price && modelResults.valuation.dcf_implied_share_price ? (
                      <p className={`text-2xl font-semibold ${((modelResults.valuation.dcf_implied_share_price / modelResults.valuation.consensus_target_price - 1) * 100) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {(((modelResults.valuation.dcf_implied_share_price / modelResults.valuation.consensus_target_price - 1) * 100) >= 0 ? '+' : '')}
                        {((modelResults.valuation.dcf_implied_share_price / modelResults.valuation.consensus_target_price - 1) * 100).toFixed(1)}%
                      </p>
                    ) : (
                      <p className="text-2xl font-semibold">N/A</p>
                    )}
                  </div>
                  
                  {/* LBO Specific Metrics - Conditionally render if LBO data exists */}
                  {modelResults.valuation.lbo_analysis && (
                    <>
                      <div className="p-4 bg-neutral-50 rounded-lg">
                        <h3 className="text-sm text-neutral-500">LBO IRR</h3>
                        <p className="text-2xl font-semibold">
                          {(modelResults.valuation.lbo_analysis.irr * 100 || 0).toFixed(1)}%
                        </p>
                      </div>
                      <div className="p-4 bg-neutral-50 rounded-lg">
                        <h3 className="text-sm text-neutral-500">LBO Payback Period</h3>
                        <p className="text-2xl font-semibold">
                          {(modelResults.valuation.lbo_analysis.payback_period || 0).toFixed(1)} years
                        </p>
                      </div>
                       <div className="p-4 bg-neutral-50 rounded-lg">
                        <h3 className="text-sm text-neutral-500">LBO MoIC</h3>
                        <p className="text-2xl font-semibold">
                          {(modelResults.valuation.lbo_analysis.moic || 0).toFixed(1)}x
                        </p>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <p className="text-neutral-500">
                  {modelId ? "Loading model results..." : "Please create a model in the Assumptions tab first."}
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="heatmap" className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Sensitivity Analysis</CardTitle></CardHeader>
            <CardContent>
              {modelId && modelResults ? (
                <div className="p-4">
                  <p className="mb-4">Equity IRR Heat-map (WACC vs Debt/EBITDA)</p>
                  {Array.isArray(modelResults.capital_structure_grid) && modelResults.capital_structure_grid.length > 0 ? (
                    (() => {
                      // Build unique sorted label arrays
                      const gridData = modelResults.capital_structure_grid;
                      const uniqueDebtToEbitda: number[] = Array.from(new Set<number>(gridData.map((d: any) => d.debt_to_ebitda))).sort((a, b) => a - b);
                      const uniqueWacc: number[] = Array.from(new Set<number>(gridData.map((d: any) => +(d.wacc * 100).toFixed(1)))).sort((a, b) => b - a); // Descending for visual

                      // Build matrix of equity_irr (% terms)
                      const matrix: number[][] = uniqueWacc.map(() => new Array(uniqueDebtToEbitda.length).fill(0));
                      gridData.forEach((row: any) => {
                        const xIndex = uniqueDebtToEbitda.indexOf(row.debt_to_ebitda);
                        const yIndex = uniqueWacc.indexOf(+(row.wacc * 100).toFixed(1));
                        if (xIndex!==-1 && yIndex!==-1){
                           matrix[yIndex][xIndex] = row.equity_irr*100; // convert to %
                        }
                      });

                      return (
                        <div className="bg-neutral-100 p-6 rounded-lg">
                          <HeatmapChart
                            data={matrix}
                            xLabels={uniqueDebtToEbitda.map((v:number)=>`${v.toFixed(1)}x`)}
                            yLabels={uniqueWacc.map((v:number)=>`${v.toFixed(1)}%`)}
                            title="Equity IRR (%) across Capital Structure"
                          />
                        </div>
                      );
                    })()
                  ) : (
                    <p className="text-neutral-500">Capital structure grid data not available for heat-map.</p>
                  )}
                </div>
              ) : (<p className="text-neutral-500">Please create a model in the Assumptions tab first.</p>)}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="export" className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Export Options</CardTitle></CardHeader>
            <CardContent>
              {modelId ? (
                <>
                  {(exportType && exportProgress > 0 && exportProgress < 100) && (
                    <div className="mb-4">
                      <p className="mb-2">Exporting {exportType}: {exportProgress.toFixed(0)}%</p>
                      <Progress value={exportProgress} className="w-full" />
                    </div>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="border rounded-lg p-6">
                      <h3 className="text-xl font-semibold mb-2">Excel Export</h3>
                      <p className="text-neutral-600 mb-4">Export a detailed Excel model with all calculations, assumptions, and results.</p>
                      <Button onClick={() => handleExport('Excel')} disabled={!!exportType && exportType !== 'Excel' || (exportType === 'Excel' && exportProgress > 0 && exportProgress < 100)}>
                        {(exportType === 'Excel' && exportProgress > 0 && exportProgress < 100) ? `Exporting... (${exportProgress.toFixed(0)}%)` : "Export to Excel"}
                      </Button>
                    </div>
                    <div className="border rounded-lg p-6">
                      <h3 className="text-xl font-semibold mb-2">PowerPoint Export</h3>
                      <p className="text-neutral-600 mb-4">Export a presentation-ready PowerPoint with key findings and visualizations.</p>
                      <Button onClick={() => handleExport('PPT')} disabled={!!exportType && exportType !== 'PPT' || (exportType === 'PPT' && exportProgress > 0 && exportProgress < 100)}>
                        {(exportType === 'PPT' && exportProgress > 0 && exportProgress < 100) ? `Exporting... (${exportProgress.toFixed(0)}%)` : "Export to PowerPoint"}
                      </Button>
                    </div>
                  </div>
                </>
              ) : (<p className="text-neutral-500">Please create a model in the Assumptions tab first.</p>)}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}