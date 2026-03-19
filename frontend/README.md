# AI Product Manager Agent - Frontend

A modern React frontend for the AI Product Manager Agent system, built with TypeScript and TailwindCSS.

## 🎯 Features

- **Modern UI**: Clean, responsive design with TailwindCSS
- **Real-time Updates**: WebSocket support for live workflow progress
- **Streaming Mode**: Toggle between standard and streaming execution
- **Interactive Results**: Collapsible sections for organized viewing
- **Error Handling**: Comprehensive error states and user feedback
- **Loading States**: Beautiful loading indicators and progress tracking

## 🛠️ Technology Stack

- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe development
- **TailwindCSS**: Utility-first CSS framework
- **Lucide React**: Beautiful icon library
- **Axios**: HTTP client for API communication
- **WebSocket**: Real-time communication with backend

## 📁 Project Structure

```
frontend/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── components/          # React components
│   │   ├── ProductIdeaForm.tsx
│   │   ├── ResultsDisplay.tsx
│   │   ├── LoadingSpinner.tsx
│   │   └── ErrorAlert.tsx
│   ├── services/           # API and WebSocket services
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── hooks/             # Custom React hooks
│   │   └── useWebSocket.ts
│   ├── types/             # TypeScript type definitions
│   │   └── index.ts
│   ├── utils/             # Utility functions
│   ├── App.tsx             # Main application component
│   ├── index.tsx           # Application entry point
│   └── index.css           # Global styles
├── package.json            # Dependencies and scripts
└── tailwind.config.js     # TailwindCSS configuration
```

## 🚀 Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend server running on `http://localhost:8000`

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Environment Variables

Create a `.env` file in the frontend root:

```env
REACT_APP_API_URL=http://localhost:8000
```

## 🔧 Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

## 🎨 UI Components

### ProductIdeaForm
- Input form for product ideas
- Thread ID support for conversation memory
- Legacy mode toggle
- Validation and error handling

### ResultsDisplay
- Collapsible sections for organized viewing
- Product vision, PRD, architecture, and tickets
- Beautiful formatting and typography

### LoadingSpinner
- Animated loading indicators
- Multiple sizes and text support
- Consistent with app theme

### ErrorAlert
- Dismissible error messages
- Consistent styling and icons
- Accessibility support

## 🔄 WebSocket Integration

The frontend supports real-time updates through WebSocket connections:

- **Connection Management**: Automatic reconnection with exponential backoff
- **Message Handling**: Typed message processing
- **Status Indicators**: Visual connection status
- **Live Progress**: Real-time workflow step updates

## 📱 Responsive Design

The application is fully responsive:

- **Mobile**: Optimized for screens 320px and up
- **Tablet**: Enhanced experience for 768px and up
- **Desktop**: Full-featured experience for 1024px and up
- **Touch Support**: Optimized for touch interactions

## 🎨 Theming

The application uses a consistent color scheme:

- **Primary**: Blue tones for main actions
- **Secondary**: Gray tones for neutral elements
- **Success**: Green tones for positive feedback
- **Error**: Red tones for error states
- **Warning**: Orange tones for cautions

## 🔧 Development

### Code Style

- **TypeScript**: Strict type checking
- **ESLint**: Code quality enforcement
- **Prettier**: Consistent formatting
- **Component-Based**: Modular, reusable components

### Build Process

- **Development**: Fast refresh with HMR
- **Production**: Optimized bundles with code splitting
- **Asset Optimization**: Image and font optimization
- **Browser Support**: Modern browsers with fallbacks

## 🚀 Deployment

### Build for Production

```bash
npm run build
```

The build will be created in the `build/` directory, ready for deployment.

### Environment Configuration

- **Development**: Local development with hot reload
- **Staging**: Pre-production testing environment
- **Production**: Optimized for performance

## 🔗 API Integration

The frontend communicates with the backend through:

- **REST API**: Standard HTTP requests
- **WebSocket**: Real-time bidirectional communication
- **Error Handling**: Comprehensive error management
- **Retry Logic**: Automatic retry with backoff

## 🧪 Testing

```bash
# Run unit tests
npm test

# Run tests in watch mode
npm test --watch

# Generate coverage report
npm test --coverage
```

## 📊 Performance

- **Bundle Size**: Optimized for fast loading
- **Code Splitting**: Lazy loading for better performance
- **Caching**: Proper cache headers and strategies
- **Images**: Optimized images with WebP support

## 🔒 Security

- **HTTPS**: Secure communication in production
- **CORS**: Proper cross-origin configuration
- **Input Validation**: Client-side validation
- **XSS Protection**: Safe rendering practices

## 🤝 Contributing

1. Follow the existing code style
2. Write tests for new features
3. Update documentation
4. Use semantic commit messages
5. Ensure responsive design

## 📄 License

This project is licensed under the MIT License.
