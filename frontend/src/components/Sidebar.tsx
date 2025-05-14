import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search } from 'lucide-react';
import api from '@/lib/api';
import { useRecentTickers } from '@/hooks/useRecentTickers';


export default function Sidebar() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const navigate = useNavigate();
  const { recentTickers, addRecentTicker } = useRecentTickers();

  // Fetch recent analyses from the API (will be used later)
  useQuery({
    queryKey: ['recentAnalyses'],
    queryFn: async () => {
      const response = await api.get('/api/recent-analyses');
      return response.data.recent_analyses || [];
    },
  });

  // Handle search input change
  const handleSearchChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);

    if (query.length >= 2) {
      try {
        const response = await api.get(`/api/search?q=${encodeURIComponent(query)}`);
        setSearchResults(response.data.results || []);
      } catch (error) {
        console.error('Search error:', error);
        setSearchResults([]);
      }
    } else {
      setSearchResults([]);
    }
  };

  // Handle search result selection
  const handleSelectResult = (ticker: string, companyName: string) => {
    addRecentTicker({ ticker, companyName });
    navigate(`/app/model/${ticker}`);
    setSearchQuery('');
    setSearchResults([]);
  };

  return (
    <aside className="w-60 h-screen bg-neutral-50 border-r border-neutral-200 flex flex-col">
      <div className="p-4">
        <h2 className="text-lg font-semibold mb-4">CapitalCanvas</h2>
        
        {/* Search Bar */}
        <div className="relative mb-6">
          <Input
            type="text"
            placeholder="Search ticker or company..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="pl-9"
          />
          <Search className="absolute left-3 top-3 h-4 w-4 text-neutral-400" />
          
          {/* Search Results Dropdown */}
          {searchResults.length > 0 && (
            <div className="absolute z-10 mt-1 w-full bg-white border border-neutral-200 rounded-md shadow-md max-h-60 overflow-y-auto">
              {searchResults.map((result) => (
                <button
                  key={result.ticker}
                  className="w-full text-left px-3 py-2 hover:bg-neutral-100 flex flex-col"
                  onClick={() => handleSelectResult(result.ticker, result.company_name)}
                >
                  <span className="font-medium">{result.ticker}</span>
                  <span className="text-sm text-neutral-500">{result.company_name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        
        {/* Navigation Links */}
        <nav className="mb-6">
          <NavLink 
            to="/app/home" 
            className={({ isActive }) => 
              `flex items-center px-3 py-2 rounded-md mb-1 ${isActive ? 'bg-neutral-200 font-medium' : 'hover:bg-neutral-100'}`
            }
          >
            Dashboard
          </NavLink>
        </nav>
      </div>
      
      {/* Recent Tickers */}
      <div className="flex-1 overflow-y-auto p-4 border-t border-neutral-200">
        <h3 className="text-sm font-medium text-neutral-500 mb-3">Recent Companies</h3>
        <div className="space-y-2">
          {recentTickers.length > 0 ? (
            recentTickers.map((item: { ticker: string; companyName: string }) => (
              <NavLink
                key={item.ticker}
                to={`/app/model/${item.ticker}`}
                className={({ isActive }) =>
                  `flex items-center px-3 py-2 rounded-md text-sm ${isActive ? 'bg-neutral-200 font-medium' : 'hover:bg-neutral-100'}`
                }
              >
                <div>
                  <div className="font-medium">{item.ticker}</div>
                  <div className="text-xs text-neutral-500">{item.companyName}</div>
                </div>
              </NavLink>
            ))
          ) : (
            <p className="text-sm text-neutral-500 italic px-3">No recent companies</p>
          )}
        </div>
      </div>
      
      {/* User Section */}
      <div className="p-4 border-t border-neutral-200">
        <Button 
          variant="ghost" 
          className="w-full justify-start" 
          onClick={() => navigate('/app/settings')}
        >
          Settings
        </Button>
        <Button 
          variant="ghost" 
          className="w-full justify-start text-destructive" 
          onClick={() => {
            localStorage.removeItem('auth_token');
            navigate('/signin');
          }}
        >
          Sign Out
        </Button>
      </div>
    </aside>
  );
}
