# Project Structure

```
media-organizer-pro/
├── media_organizer.py       # Core CLI organizer with IMDB integration
├── imdb_lookup.py           # IMDB/OMDb API client
├── standalone_backend.py    # Standalone FastAPI backend (port 8000)
├── gpu_converter_service.py # GPU video conversion service (port 8888)
├── requirements.txt         # Root Python dependencies
├── package.json             # Root scripts (concurrently runs all services)
├── start.sh                 # Shell script to start all services
│
└── webapp/                  # Full-stack web application
    ├── docker-compose.yml   # Container orchestration
    │
    ├── backend/             # FastAPI backend
    │   ├── app/
    │   │   ├── main.py      # FastAPI app entry point
    │   │   ├── api/
    │   │   │   └── routes.py    # API endpoints
    │   │   ├── core/
    │   │   │   └── config.py    # Settings (pydantic-settings)
    │   │   ├── models/
    │   │   │   └── schemas.py   # Pydantic request/response models
    │   │   └── services/
    │   │       ├── media_service.py    # File organization logic
    │   │       └── video_converter.py  # GPU conversion logic
    │   ├── uploads/         # Uploaded files
    │   ├── temp/            # Temporary processing
    │   └── output/          # Converted output
    │
    └── frontend/            # React SPA
        ├── src/
        │   ├── App.jsx      # Main app component
        │   ├── main.jsx     # Entry point
        │   ├── index.css    # Global styles
        │   ├── components/  # React components
        │   │   ├── ui/      # Reusable UI primitives (Button, Card, Input)
        │   │   ├── Header.jsx
        │   │   ├── FileUpload.jsx
        │   │   ├── OperationPanel.jsx
        │   │   └── ...
        │   └── lib/
        │       ├── api.js   # Axios API client
        │       └── utils.js # Utility functions (cn for classnames)
        ├── tailwind.config.js  # TailwindCSS + DaisyUI themes
        └── vite.config.js
```

## Architecture Patterns

- **Backend**: Layered architecture (routes → services → models)
- **Frontend**: Component-based with co-located UI primitives
- **API**: RESTful with WebSocket support for real-time progress
- **Config**: Environment-based via `.env` files and pydantic-settings
