import React from 'react';
import { BackgroundGradient } from '../aceternity/background-gradient';
import { HoverBorderGradientButton } from '../aceternity/hover-border-gradient';

export const GradientExample: React.FC = () => {
  return (
    <div className="max-w-5xl mx-auto py-12 px-6 space-y-8">
      {/* Background Gradient Example */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Background Gradient</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <BackgroundGradient className="p-6">
            <div className="text-center">
              <h3 className="text-xl font-semibold mb-2">Financial Analysis</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Comprehensive financial modeling and valuation tools
              </p>
            </div>
          </BackgroundGradient>
          
          <BackgroundGradient className="p-6">
            <div className="text-center">
              <h3 className="text-xl font-semibold mb-2">Market Insights</h3>
              <p className="text-gray-600 dark:text-gray-300">
                Real-time data and industry benchmarks
              </p>
            </div>
          </BackgroundGradient>
        </div>
      </div>

      {/* Hover Border Gradient Buttons */}
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">Hover Border Gradient Buttons</h2>
        <div className="flex flex-wrap gap-4">
          <HoverBorderGradientButton>
            Get Started
          </HoverBorderGradientButton>
          
          <HoverBorderGradientButton className="px-6 py-3">
            Learn More
          </HoverBorderGradientButton>
          
          <HoverBorderGradientButton className="rounded-full px-6">
            Sign Up
          </HoverBorderGradientButton>
          
          <HoverBorderGradientButton className="bg-black text-white dark:bg-gray-800">
            Premium
          </HoverBorderGradientButton>
          
          <HoverBorderGradientButton className="border border-gray-200 dark:border-gray-700">
            Contact Us
          </HoverBorderGradientButton>
        </div>
      </div>
    </div>
  );
};

export default GradientExample;
