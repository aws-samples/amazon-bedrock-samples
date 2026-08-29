# React + AWS Cloudscape Migration

This document outlines the migration from the original Bootstrap-based UI to a modern React application using AWS Cloudscape Design System.

## Architecture

### Frontend Stack
- **React 18** with TypeScript
- **AWS Cloudscape Design System** for UI components
- **Vite** for fast development and building
- **Axios** for API communication

### Backend Integration
- **FastAPI** serves both legacy and React UIs
- **API routes** prefixed with `/api` for React app
- **Dual routing** supports gradual migration

## Development Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+ with existing dependencies

### Quick Start

```bash
# Development mode (runs both FastAPI and React)
./run_dev.sh

# Production build
./build_react.sh
./run_web.sh
```

### Manual Setup

```bash
# Install React dependencies
cd src/frontend/react
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Component Mapping

| Original (Bootstrap) | New (Cloudscape) | Status |
|---------------------|------------------|---------|
| Bootstrap forms | Form, FormField, Input | ✅ Complete |
| Bootstrap tables | Table with editing | ✅ Complete |
| Bootstrap cards | Container, Header | ✅ Complete |
| Bootstrap buttons | Button variants | ✅ Complete |
| Log viewer | Textarea with tailing | ✅ Complete |
| Status indicators | StatusIndicator | ✅ Complete |

## Key Features

### ✅ Implemented
- **Configuration Management** - Form with validation
- **Blueprint Fetching** - Async data loading
- **Instructions Table** - Editable table with real-time updates
- **Optimizer Controls** - Start/stop with status indicators
- **Log Viewer** - Real-time log tailing with file selection
- **Schema Viewer** - JSON schema display
- **State Management** - React Context for global state

### 🔄 In Progress
- Error handling with Cloudscape notifications
- Advanced table features (sorting, filtering)
- WebSocket integration for real-time updates

### 📋 Planned
- Dark mode support
- Mobile responsiveness improvements
- Advanced form validation
- Export/import functionality

## File Structure

```
src/frontend/react/
├── src/
│   ├── components/          # React components
│   │   ├── ConfigurationForm.tsx
│   │   ├── InstructionsTable.tsx
│   │   ├── OptimizerControls.tsx
│   │   ├── LogViewer.tsx
│   │   └── SchemaViewer.tsx
│   ├── contexts/           # React Context providers
│   │   └── AppContext.tsx
│   ├── services/           # API service layer
│   │   └── api.ts
│   ├── types/              # TypeScript interfaces
│   │   └── index.ts
│   ├── App.tsx             # Main app component
│   └── main.tsx            # React entry point
├── package.json            # Dependencies
├── vite.config.ts          # Vite configuration
└── tsconfig.json           # TypeScript configuration
```

## API Integration

The React app communicates with the FastAPI backend through:

- **REST API** calls using Axios
- **Dual routing** - endpoints available at both `/endpoint` and `/api/endpoint`
- **Real-time updates** via polling (WebSocket planned)

## Deployment

### Development
```bash
./run_dev.sh
# React: http://localhost:3000
# FastAPI: http://localhost:8000
```

### Production
```bash
./build_react.sh
./run_web.sh
# Unified app: http://localhost:8000
```

## Migration Benefits

1. **Modern UI/UX** - AWS Cloudscape provides consistent, professional interface
2. **Better Performance** - React's virtual DOM and component optimization
3. **Type Safety** - TypeScript prevents runtime errors
4. **Maintainability** - Component-based architecture
5. **Accessibility** - Built-in WCAG compliance
6. **Responsive Design** - Mobile-friendly layouts
7. **Developer Experience** - Hot reload, better debugging

## Next Steps

1. **Test the current implementation**
2. **Add error handling and notifications**
3. **Implement WebSocket for real-time updates**
4. **Add advanced table features**
5. **Optimize performance and bundle size**
6. **Add comprehensive testing**

## Troubleshooting

### Common Issues

**React app not loading:**
- Ensure Node.js 18+ is installed
- Run `npm install` in `src/frontend/react/`
- Check console for build errors

**API calls failing:**
- Verify FastAPI is running on port 8000
- Check network tab for failed requests
- Ensure API routes are properly prefixed

**Build failures:**
- Clear `node_modules` and reinstall
- Check TypeScript errors in console
- Verify all imports are correct