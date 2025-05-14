import React from 'react';
import { TypewriterEffect } from '../aceternity/typewriter-effect';
import { Card } from '../aceternity/card';
import { CardContent } from '../aceternity/card-content';

export const TypewriterExample: React.FC = () => {
  return (
    <Card className="w-full max-w-md mx-auto bg-white/10 backdrop-blur-md border border-gray-200 dark:border-gray-800 rounded-xl shadow-lg">
      <CardContent className="p-6 flex flex-col items-center justify-center text-center">
        <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
          <TypewriterEffect 
            text="The happier way to model financials" 
            typingSpeed={80}
            delayBeforeStart={500}
            className="text-gradient-primary font-bold"
            cursorClassName="text-blue-500"
          />
        </h2>
        <p className="text-gray-600 dark:text-gray-300 mt-4">
          Experience our intuitive financial modeling platform
        </p>
      </CardContent>
    </Card>
  );
};

export default TypewriterExample;
