# YouTube ELT Pipeline Dashboard

A simple Streamlit dashboard for visualizing YouTube video analytics data from the ELT pipeline.

## Features

- 📊 **Key Metrics Overview**: Total videos, views, engagement rates
- 📈 **Views Timeline**: Track performance over time
- 🎯 **Content Category Analysis**: Performance by video type
- 🎪 **Performance Scatter Plot**: Views vs engagement correlation
- ⏱️ **Video Length Analysis**: Optimal video duration insights
- 🔥 **Trending Videos**: Current top performers
- 🏆 **Top Videos Table**: Best performing content
- ✅ **Data Quality Status**: Pipeline health monitoring

## Quick Start

### 1. Install Dependencies
```bash
cd dashboard
pip install -r requirements.txt
```

### 2. Set Environment Variables
```bash
# Copy from main .env file or set directly
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=password
export POSTGRES_DB=postgres
```

### 3. Run Dashboard
```bash
streamlit run app.py
```

### 4. Access Dashboard
Open http://localhost:8501 in your browser

## Configuration

The dashboard connects to your PostgreSQL database using environment variables:

- `POSTGRES_HOST` - Database host (default: localhost)
- `POSTGRES_PORT` - Database port (default: 5432)
- `POSTGRES_USER` - Database username (default: postgres)
- `POSTGRES_PASSWORD` - Database password (default: password)
- `POSTGRES_DB` - Database name (default: postgres)

## Features Details

### Interactive Filters
- **Date Range**: Filter videos by publication date
- **Content Categories**: Select specific video categories
- **Auto-refresh**: Automatic data updates every 30 seconds

### Visualizations
- Line charts for timeline analysis
- Pie charts for distribution analysis
- Bar charts for category comparison
- Scatter plots for correlation analysis
- Metrics cards for KPI tracking

### Data Quality Monitoring
- Data freshness indicators
- Record completeness metrics
- Quality issue detection
- Pipeline health status

## Docker Integration

To run the dashboard in Docker alongside the main pipeline:

```yaml
# Add to docker-compose.yml
dashboard:
  build: ./dashboard
  ports:
    - "8501:8501"
  environment:
    - POSTGRES_HOST=postgres
    - POSTGRES_PORT=5432
    - POSTGRES_USER=postgres
    - POSTGRES_PASSWORD=password
    - POSTGRES_DB=postgres
  depends_on:
    - postgres
```

## Development

### Local Development
```bash
# Install in development mode
pip install -r requirements.txt
pip install streamlit[dev]

# Run with hot reload
streamlit run app.py --server.runOnSave true
```

### Adding New Charts
1. Create new visualization function in `app.py`
2. Add to main dashboard layout
3. Test with sample data
4. Add configuration options if needed

### Customization
- Modify color schemes in Plotly configurations
- Add new metrics calculations
- Extend filtering capabilities
- Add export functionality

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check environment variables
- Verify network connectivity
- Confirm database schema exists

### No Data Display
- Run the ELT pipeline first to populate data
- Check core.videos table has records
- Verify data quality checks pass
- Review database permissions

### Performance Issues
- Enable data caching (enabled by default)
- Limit date ranges for large datasets
- Optimize database queries
- Consider data sampling for very large datasets

## Screenshots

*Dashboard will display various charts and metrics once connected to data*

## Integration with Pipeline

The dashboard automatically reads from the same PostgreSQL database used by the ELT pipeline:

1. **Staging Data**: Raw video information
2. **Core Data**: Transformed and enriched analytics
3. **Quality Metrics**: Data validation results

## Future Enhancements

- Real-time data streaming
- Advanced analytics and ML insights
- Export capabilities (PDF, CSV)
- User authentication
- Multi-channel support
- Custom alert configurations