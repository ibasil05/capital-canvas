import { getAuthToken } from './auth';

// WebSocket connection options
interface WebSocketOptions {
  onOpen?: (event: Event) => void;
  onMessage?: (event: MessageEvent) => void;
  onError?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
}

// Create and manage WebSocket connections
export const createWebSocket = (path: string, options: WebSocketOptions = {}) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  // Convert http/https to ws/wss
  const wsBaseUrl = baseUrl.replace(/^http/, 'ws');
  const token = getAuthToken();
  
  // Create WebSocket connection with auth token
  const ws = new WebSocket(`${wsBaseUrl}${path}`);
  
  // Set up event handlers
  if (options.onOpen) {
    ws.addEventListener('open', options.onOpen);
  }
  
  if (options.onMessage) {
    ws.addEventListener('message', options.onMessage);
  }
  
  if (options.onError) {
    ws.addEventListener('error', options.onError);
  }
  
  if (options.onClose) {
    ws.addEventListener('close', options.onClose);
  }
  
  return ws;
};

// Define the structure of the progress message from the WebSocket
interface ExportProgressMessage {
  job_id?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'error';
  pct_complete?: number;
  file_url?: string;
  error_message?: string;
  message?: string; // Generic message for errors from WebSocket itself
}

// Create a WebSocket connection for export progress
export const createExportProgressWebSocket = (jobId: string, onMessageCallback: (data: ExportProgressMessage) => void) => {
  return createWebSocket(`/ws/progress/${jobId}`, {
    onMessage: (event) => {
      try {
        const data: ExportProgressMessage = JSON.parse(event.data as string);
        onMessageCallback(data); // Pass the parsed object to the callback
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        // Send a structured error back to the main handler if parsing fails
        onMessageCallback({
          status: 'error',
          error_message: 'Failed to parse message from server.',
        });
      }
    },
    onError: (event) => {
      console.error('WebSocket error event:', event);
      // Send a structured error back to the main handler
      onMessageCallback({
        status: 'error',
        error_message: 'WebSocket connection error.',
      });
    },
    onClose: (event) => {
      console.log('WebSocket connection closed:', event.code, event.reason);
      // Optionally, notify the main handler about the closure if it's unexpected
      // For example, if it wasn't closed by the client after 'completed' or 'failed' status
      // This might require more state management to determine if the close was expected.
    }
  });
};
