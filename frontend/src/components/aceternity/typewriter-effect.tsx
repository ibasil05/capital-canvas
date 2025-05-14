import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface TypewriterEffectProps {
  text: string;
  className?: string;
  cursorClassName?: string;
  typingSpeed?: number;
  delayBeforeStart?: number;
  showCursor?: boolean;
  onComplete?: () => void;
}

export const TypewriterEffect: React.FC<TypewriterEffectProps> = ({
  text,
  className = '',
  cursorClassName = '',
  typingSpeed = 100,
  delayBeforeStart = 0,
  showCursor = true,
  onComplete,
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    // Reset state when text changes
    setDisplayedText('');
    setCurrentIndex(0);
    setIsTyping(false);

    // Delay before starting to type
    const startDelay = setTimeout(() => {
      setIsTyping(true);
    }, delayBeforeStart);

    return () => clearTimeout(startDelay);
  }, [text, delayBeforeStart]);

  useEffect(() => {
    if (!isTyping) return;

    if (currentIndex < text.length) {
      const typingTimer = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, typingSpeed);

      return () => clearTimeout(typingTimer);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, isTyping, text, typingSpeed, onComplete]);

  return (
    <div className={cn('inline-block', className)}>
      <span>{displayedText}</span>
      {showCursor && currentIndex <= text.length && (
        <span className={cn('animate-pulse', cursorClassName)}>|</span>
      )}
    </div>
  );
};

export default TypewriterEffect;
