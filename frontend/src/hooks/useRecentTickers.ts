import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface TickerItem {
  ticker: string;
  companyName: string;
}

interface RecentTickersState {
  recentTickers: TickerItem[];
  addRecentTicker: (ticker: TickerItem) => void;
  clearRecentTickers: () => void;
}

// Create a Zustand store with persistence
export const useRecentTickers = create<RecentTickersState>()(
  persist(
    (set) => ({
      recentTickers: [],
      
      // Add a ticker to the recent list (or move it to the top if it already exists)
      addRecentTicker: (ticker: TickerItem) => 
        set((state) => {
          // Remove the ticker if it already exists
          const filteredTickers = state.recentTickers.filter(
            (item) => item.ticker !== ticker.ticker
          );
          
          // Add the ticker to the beginning of the array
          return {
            recentTickers: [
              ticker,
              ...filteredTickers,
            ].slice(0, 10), // Keep only the 10 most recent tickers
          };
        }),
      
      // Clear all recent tickers
      clearRecentTickers: () => set({ recentTickers: [] }),
    }),
    {
      name: 'capital-canvas-recent-tickers', // Name for localStorage
    }
  )
);
