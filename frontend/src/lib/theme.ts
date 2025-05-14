// Theme configuration for Tailwind CSS

// Colors based on Notion-style design
export const themeColors = {
  primary: {
    50: '#e6f0ff',
    100: '#cce0ff',
    200: '#99c2ff',
    300: '#66a3ff',
    400: '#3385ff',
    500: '#0066ff', // Primary brand color
    600: '#0052cc',
    700: '#003d99',
    800: '#002966',
    900: '#001433',
  },
  neutral: {
    50: '#f9f9f9',
    100: '#f2f2f2',
    200: '#e6e6e6',
    300: '#cccccc',
    400: '#b3b3b3',
    500: '#999999',
    600: '#737373',
    700: '#595959',
    800: '#333333', // Main text color
    900: '#1a1a1a',
  },
};

// Typography settings
export const typography = {
  fontFamily: {
    sans: ['Inter', 'sans-serif'],
  },
  fontSize: {
    xs: '0.75rem',    // 12px
    sm: '0.875rem',   // 14px
    base: '1rem',     // 16px
    lg: '1.125rem',   // 18px
    xl: '1.25rem',    // 20px
    '2xl': '1.5rem',  // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem', // 36px
  },
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
};

// Spacing and sizing
export const spacing = {
  // Base spacing unit: 4px
  '0': '0',
  '1': '0.25rem',   // 4px
  '2': '0.5rem',    // 8px
  '3': '0.75rem',   // 12px
  '4': '1rem',      // 16px
  '5': '1.25rem',   // 20px
  '6': '1.5rem',    // 24px - Primary spacing
  '8': '2rem',      // 32px
  '10': '2.5rem',   // 40px
  '12': '3rem',     // 48px
  '16': '4rem',     // 64px
  '20': '5rem',     // 80px
  '24': '6rem',     // 96px
};

// Border radius
export const borderRadius = {
  'none': '0',
  'sm': '0.25rem',   // 4px
  'md': '0.5rem',    // 8px
  'lg': '0.75rem',   // 12px
  'xl': '1rem',      // 16px - Card radius
  '2xl': '1.5rem',   // 24px
  'full': '9999px',  // Circular
};

// Shadows
export const shadows = {
  'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
};

// Export the complete theme configuration
export const themeConfig = {
  colors: themeColors,
  typography,
  spacing,
  borderRadius,
  shadows,
};

export default themeConfig;
