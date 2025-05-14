import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Search, Clock, ArrowRight, BarChart2 } from 'lucide-react';
import api from '@/lib/api';
import { useRecentTickers } from '@/hooks/useRecentTickers';
import { Card } from '@/components/aceternity/card';
import { CardContent } from '@/components/aceternity/card-content';
import { Input } from '@/components/aceternity/input';
import { Button } from '@/components/aceternity/button';

interface CompanySearchResult {
  ticker: string;
  company_name: string;
  exchange?: string;
  sector?: string;
}

export default function Home() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<CompanySearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const navigate = useNavigate();
  const { addRecentTicker } = useRecentTickers();
  
  // Fetch recent analyses for the dashboard
  const { data: recentAnalyses, isLoading } = useQuery({
    queryKey: ['recentAnalyses'],
    queryFn: async () => {
      const response = await api.get('/api/recent-analyses');
      return response.data.recent_analyses || [];
    },
  });
  
  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };
  
  // Handle search form submission
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!searchQuery.trim()) return;
    
    setIsSearching(true);
    
    try {
      const response = await api.get(`/api/search?q=${encodeURIComponent(searchQuery)}`);
      if (Array.isArray(response.data)) {
        setSearchResults(response.data);
      } else {
        console.warn('Search API did not return an array:', response.data);
        setSearchResults([]);
      }
    } catch (error) {
      console.error('Search error:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };
  
  // Handle company selection
  const handleSelectCompany = (company: CompanySearchResult) => {
    addRecentTicker({
      ticker: company.ticker,
      companyName: company.company_name,
    });
    navigate(`/app/model/${company.ticker}`);
  };
  
  return (
    <>
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-8"
      >
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="space-y-2 text-center mb-12"
        >
          <div className="flex items-center justify-center mb-2">
            <BarChart2 className="h-10 w-10 text-blue-600 mr-3" />
            <h1 className="text-4xl font-bold tracking-tight text-neutral-900 dark:text-neutral-50">
              Your Dashboard
            </h1>
          </div>
          <p className="text-lg text-neutral-500 dark:text-neutral-400">
            Search for companies and view your recent analysis.
          </p>
        </motion.div>
        
        {/* Search Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <Card className="mb-8 shadow-lg border-0 bg-white/80 backdrop-blur-sm">
            <CardContent>
              <div className="flex items-center mb-4">
                <Search className="h-5 w-5 text-blue-500 mr-2" />
                <h2 className="text-xl font-medium">Search Companies</h2>
              </div>
              
              <form onSubmit={handleSearch} className="flex gap-2 mb-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-neutral-400" />
                  <Input
                    type="text"
                    placeholder="Search by ticker or company name"
                    value={searchQuery}
                    onChange={handleSearchChange}
                    className="pl-9"
                  />
                </div>
                <Button 
                  type="submit" 
                  disabled={isSearching}
                  isLoading={isSearching}
                  className="bg-black text-white hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200 shrink-0"
                >
                  {isSearching ? 'Searching...' : 'Search'}
                </Button>
              </form>
              
              {/* Search Results */}
              {searchResults.length > 0 && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.2 }}
                  className="mb-8"
                >
                  <h3 className="text-lg font-medium mb-3">Search Results</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {searchResults.map((company, index) => (
                      <motion.div
                        key={company.ticker || `search-result-${index}`} // Use ticker or index as key
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.2, delay: index * 0.05 }}
                        className="bg-white/90 dark:bg-neutral-800/90 backdrop-blur-sm border border-neutral-200 dark:border-neutral-700 rounded-lg p-4 hover:shadow-lg cursor-pointer transition-shadow"
                        onClick={() => company.ticker && handleSelectCompany(company)} // Ensure company.ticker exists before selecting
                      >
                        <h4 className="font-semibold text-neutral-800 dark:text-neutral-100 truncate">{company.company_name || 'Unnamed Company'}</h4>
                        <p className="text-sm text-neutral-600 dark:text-neutral-400">{company.ticker || 'N/A'}</p>
                        {company.exchange && <p className="text-xs text-neutral-500 dark:text-neutral-500">Exchange: {company.exchange}</p>}
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </CardContent>
          </Card>
        </motion.div>
        
        {/* Recent Analysis */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Card className="shadow-lg border-0 bg-white/80 backdrop-blur-sm">
            <CardContent>
              <div className="flex items-center mb-4">
                <Clock className="h-5 w-5 text-indigo-500 mr-2" />
                <h2 className="text-xl font-medium">Recent Analysis</h2>
              </div>
              
              {isLoading ? (
                <div className="py-8 text-center">
                  <motion.div 
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    className="inline-block mb-2"
                  >
                    <Clock className="h-6 w-6 text-indigo-400" />
                  </motion.div>
                  <p className="text-neutral-500">Loading recent analysis...</p>
                </div>
              ) : recentAnalyses && recentAnalyses.length > 0 ? (
                <div className="bg-white/90 backdrop-blur-sm border border-neutral-200 rounded-lg overflow-hidden">
                  {recentAnalyses.map((analysis: any, index: number) => (
                    <motion.div 
                      key={`${analysis.ticker}-${analysis.viewed_at}`}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2, delay: index * 0.05 }}
                      className={`p-4 hover:bg-indigo-50/50 cursor-pointer flex justify-between items-center ${
                        index !== recentAnalyses.length - 1 ? 'border-b border-neutral-100' : ''
                      }`}
                      onClick={() => navigate(`/app/model/${analysis.ticker}`)}
                    >
                      <div className="flex items-start">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mr-3 text-white font-medium shadow-sm">
                          {analysis.ticker && typeof analysis.ticker === 'string' ? analysis.ticker.substring(0, 1).toUpperCase() : 'N/A'}
                        </div>
                        <div>
                          <h3 className="font-medium text-neutral-900">{analysis.ticker || 'Unknown Ticker'}</h3>
                          <p className="text-sm text-neutral-500">{analysis.company_name || 'Unknown Company'}</p>
                          <p className="text-xs text-neutral-400">
                            {analysis.viewed_at ? new Date(analysis.viewed_at).toLocaleDateString() : 'Unknown Date'}
                          </p>
                        </div>
                      </div>
                      <Button 
                        variant="outline" 
                        size="sm"
                        className="rounded-full border-indigo-200 hover:bg-indigo-50 hover:border-indigo-300 transition-all duration-200"
                      >
                        View <ArrowRight className="ml-1 h-3 w-3" />
                      </Button>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center border border-dashed border-neutral-200 rounded-lg bg-neutral-50/50">
                  <p className="text-neutral-500">No recent analysis found. Start by searching for a company above.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </>
  );
}
