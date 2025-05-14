import { Link } from 'react-router-dom';

// Import Aceternity UI components
import { Header } from '@/components/aceternity/header';
import { HeroSection } from '@/components/aceternity/hero-section';
import { CodeSnippet, CodeSnippetItem } from '@/components/aceternity/code-snippet';
import { FeaturesSection } from '@/components/aceternity/features-section';
import { FeatureCard } from '@/components/aceternity/feature-card';
import { CTASection } from '@/components/aceternity/cta-section';
import { Footer } from '@/components/aceternity/footer';
import { Button } from '@/components/aceternity/button';

export default function Landing() {
  // Icons
  const chartIcon = (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="20" x2="12" y2="10" />
      <line x1="18" y1="20" x2="18" y2="4" />
      <line x1="6" y1="20" x2="6" y2="16" />
    </svg>
  );
  
  const valuationIcon = (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"></circle>
      <polyline points="8 14 12 10 16 14"></polyline>
      <line x1="12" y1="18" x2="12" y2="10"></line>
    </svg>
  );
  
  const structureIcon = (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
      <polyline points="2 17 12 22 22 17"></polyline>
      <polyline points="2 12 12 17 22 12"></polyline>
    </svg>
  );

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-neutral-950">
      {/* Header */}
      <Header />

      <main className="flex-1">
        {/* Hero Section */}
        <HeroSection
          title="The happier way to model financials"
          subtitle="Build sophisticated financial models and capital structure analyses in minutes, not hours. Powered by real-time market data and industry-standard methodologies."
        >
          <Link to="/signup">
            <Button variant="default" size="lg" className="inline-flex items-center gap-2 bg-black text-white hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200">
              Get Started
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </Button>
          </Link>
        </HeroSection>

        {/* Animated Code Snippet */}
        <div className="py-12 px-6 bg-white dark:bg-neutral-950">
          <CodeSnippet title="Financial Model - AAPL">
            <CodeSnippetItem
              icon={chartIcon}
              title="Revenue Forecast"
              iconColor="text-green-600 dark:text-green-400"
              borderColor="border-green-300 dark:border-green-700"
              items={[
                { label: 'Annual Growth Rate', value: '8.5%', color: 'text-green-700 dark:text-green-300 font-semibold' },
                { label: '5-Year Projection', value: '$534.2B', color: 'text-green-700 dark:text-green-300 font-semibold' },
                { label: 'CAGR', value: '7.2%', color: 'text-green-600 dark:text-green-400' },
              ]}
            />
            
            <CodeSnippetItem
              icon={valuationIcon}
              title="Valuation Metrics"
              iconColor="text-blue-600 dark:text-blue-400"
              borderColor="border-blue-300 dark:border-blue-700"
              items={[
                { label: 'DCF Valuation', value: '$198.42', color: 'text-blue-700 dark:text-blue-300 font-semibold' },
                { label: 'P/E Ratio', value: '26.4x', color: 'text-blue-600 dark:text-blue-400' },
                { label: 'EV/EBITDA', value: '14.2x', color: 'text-blue-600 dark:text-blue-400' },
              ]}
            />
            
            <CodeSnippetItem
              icon={structureIcon}
              title="Capital Structure"
              iconColor="text-purple-600 dark:text-purple-400"
              borderColor="border-purple-300 dark:border-purple-700"
              items={[
                { label: 'Debt-to-Equity', value: '1.2', color: 'text-purple-700 dark:text-purple-300 font-semibold' },
                { label: 'WACC', value: '7.8%', color: 'text-purple-600 dark:text-purple-400' },
                { label: 'Interest Coverage', value: '3.5x', color: 'text-purple-600 dark:text-purple-400' },
              ]}
            />
          </CodeSnippet>
        </div>

        {/* Additional Code Snippet */}
        <div className="py-12 px-6 bg-white dark:bg-neutral-950">
          <CodeSnippet title="Financial Dashboard - AAPL">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm font-mono">
              <div className="bg-white dark:bg-neutral-900 p-4 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-sm">
                <h3 className="font-bold mb-2 text-green-800 dark:text-green-300">Revenue Growth</h3>
                <div className="flex items-center justify-between mb-1">
                  <span>2023:</span>
                  <span className="font-semibold">+6.7%</span>
                </div>
                <div className="flex items-center justify-between mb-1">
                  <span>2024 (est):</span>
                  <span className="font-semibold">+8.2%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>2025 (est):</span>
                  <span className="font-semibold">+9.1%</span>
                </div>
              </div>
              
              <div className="bg-white dark:bg-neutral-900 p-4 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-sm">
                <h3 className="font-bold mb-2 text-blue-800 dark:text-blue-300">Profit Margins</h3>
                <div className="flex items-center justify-between mb-1">
                  <span>Gross:</span>
                  <span className="font-semibold">43.2%</span>
                </div>
                <div className="flex items-center justify-between mb-1">
                  <span>Operating:</span>
                  <span className="font-semibold">30.1%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Net:</span>
                  <span className="font-semibold">25.3%</span>
                </div>
              </div>
              
              <div className="bg-white dark:bg-neutral-900 p-4 rounded-lg border border-neutral-200 dark:border-neutral-800 shadow-sm">
                <h3 className="font-bold mb-2 text-purple-800 dark:text-purple-300">Valuation</h3>
                <div className="flex items-center justify-between mb-1">
                  <span>P/E Ratio:</span>
                  <span className="font-semibold">26.4x</span>
                </div>
                <div className="flex items-center justify-between mb-1">
                  <span>EV/EBITDA:</span>
                  <span className="font-semibold">14.2x</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Target Price:</span>
                  <span className="font-semibold">$198.42</span>
                </div>
              </div>
            </div>
          </CodeSnippet>
        </div>

        {/* Features Section */}
        <FeaturesSection
          title="Powerful features for financial modeling"
          subtitle="Everything you need to build sophisticated financial models and make informed investment decisions."
        >
          <FeatureCard
            icon={chartIcon}
            title="Real-Time Data"
            description="Access financial statements, market data, and industry benchmarks updated in real-time."
            iconBgColor="bg-neutral-100 dark:bg-neutral-800"
            iconColor="text-black dark:text-white"
          />
          
          <FeatureCard
            icon={valuationIcon}
            title="DCF Valuation"
            description="Build discounted cash flow models with customizable assumptions and sensitivity analysis."
            iconBgColor="bg-neutral-100 dark:bg-neutral-800"
            iconColor="text-black dark:text-white"
          />
          
          <FeatureCard
            icon={structureIcon}
            title="Capital Structure"
            description="Optimize debt-to-equity ratios and analyze the impact on WACC and enterprise value."
            iconBgColor="bg-neutral-100 dark:bg-neutral-800"
            iconColor="text-black dark:text-white"
          />
        </FeaturesSection>
        
        {/* CTA Section */}
        <CTASection
          title="Ready to Transform Your Financial Analysis?"
          subtitle="Build sophisticated financial models with CapitalCanvas."
        >
          <Link to="/signup">
            <Button variant="default" size="lg" className="bg-black text-white hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200">
              Sign Up
            </Button>
          </Link>
          <Link to="/signin">
            <Button variant="outline" size="lg" className="border-black text-black hover:bg-neutral-100 dark:border-white dark:text-white dark:hover:bg-neutral-900">
              Sign In
            </Button>
          </Link>
        </CTASection>
      </main>
      
      <Footer />
    </div>
  );
}
