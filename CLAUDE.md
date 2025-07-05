# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a CKAN extension that provides a custom theme for UNESCO's water-related data portal. Despite the name `ckanext-theme-ejemplo` (example theme), this is a production theme specifically designed for UNESCO's water data initiatives.

## Development Commands

### Setup
```bash
# Install in development mode
pip install -e .
pip install -r requirements.txt
pip install -r dev-requirements.txt  # For testing

# Add to CKAN configuration
# Edit your CKAN config file and add 'theme_ejemplo' to ckan.plugins
```

### Testing
```bash
# Run all tests
pytest --ckan-ini=test.ini

# Run with coverage (as done in CI)
pytest --ckan-ini=test.ini --cov=ckanext.theme_ejemplo
```

### Build & Package
```bash
# Build distribution
python setup.py sdist

# Upload to PyPI
python setup.py sdist upload
```

## Architecture & Key Components

### Core Plugin Architecture

The main plugin (`ckanext/theme_ejemplo/plugin.py`) implements multiple CKAN interfaces to provide:

1. **Custom Routes** - Six specialized portals accessed via Flask blueprints:
   - `/memberstates` - UNESCO member states directory
   - `/initiatives` - Water initiatives catalog  
   - `/thematicbuilder` - Thematic dataset builder
   - `/ihpix` - IHP-IX (International Hydrological Programme) portal
   - `/iot-portal` - IoT water monitoring portal
   - `/flood-drought-portal` - Flood and drought monitoring
   - `/citizen-science-portal` - Citizen science initiatives

2. **Dataset Enhancement** - The plugin modifies dataset indexing to:
   - Convert spatial bounding boxes to WKT format for Solr indexing
   - Mark featured datasets based on admin follower count
   - Process and enhance search facets
   - Cache organization images for performance

3. **External API Integration** - Integrates with UNESCO Open Learning API to fetch water-related courses, with LRU caching for performance.

### Template Structure

Templates follow CKAN's Jinja2 pattern with custom overrides:
- `templates/home/` - Homepage components with UNESCO branding
- `templates/[portal_name]/` - Specific templates for each portal
- `templates/snippets/` - Reusable components
- All templates support internationalization (i18n)

### Performance Considerations

Recent optimizations include:
- HTTP session reuse with connection pooling
- LRU caching for external API calls
- Organization image caching
- Proper error handling and logging throughout

### Spatial Data Handling

The extension processes geospatial data using the Shapely library to convert bounding box coordinates to WKT format for proper Solr indexing. This enables spatial search capabilities across the portal.

## Important Notes

1. **CKAN Version**: Built for CKAN 2.9 (Python 2.7 support indicates this)
2. **Dependencies**: Requires ckanext-spatial, ckanext-dcat, ckanext-scheming, ckanext-schemingdcat
3. **Name Mismatch**: The internal name `theme_ejemplo` appears throughout the codebase but doesn't reflect the UNESCO-specific nature of this theme
4. **Internationalization**: Supports Arabic, Spanish, and French translations
5. **Testing**: Uses pytest with a custom test.ini configuration