# CKAN UNESCO Theme - Quick Reference for Tracking/Analytics

## Current Tracking Integration ✓

### 1. CKAN Built-in Tracking (Enabled)
- **Configuration**: `ckan.tracking_enabled` (checked in templates)
- **Data Point**: `res.tracking_summary.total` (views per resource)
- **Used in**: 
  - Resource display: shows popularity badges
  - Search results: "Popular" sort option
  - Dataset read page: fetches tracking data

### 2. Custom Tracking Models
- **MembershipRequest**: User → Organization join requests
- **BugTicket**: Issue/bug tracking system
- **FeaturedPublication**: Content curation tracking

### 3. Statistics Helpers (for dashboards)
- `theme_ejemplo_site_statistics()` → {dataset_count, organization_count, group_count}
- `get_org_statistics(org_id)` → {datasets, publications, members}
- `get_org_publications(org_id)` → filtered publications

## Key Files for Analytics Implementation

| Purpose | File | Key Function |
|---------|------|--------------|
| Track resource views | `controller.py:1149` | `include_tracking=True` |
| Display view counts | `resource_item.html:52` | `h.popular('views', res.tracking_summary.total)` |
| Sort by popularity | `search.html:49` | `views_recent desc` |
| Organization stats | `helpers.py:131` | `get_org_statistics()` |
| Site stats | `plugin.py:949` | `_get_site_statistics_uncached()` |
| People directory | `actions.py:99` | `people_list()` with filters |

## Template Locations

### Statistics Display
- `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/home/snippets/stats.html` - Site stats

### Resource/Dataset Display
- `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/snippets/resource_item.html` - Resource with views

### Dataset Listing
- `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/search.html` - Search with popularity sort

## Cache Configuration
- Member states groups: TTL configurable via `ckanext.theme_ejemplo.groups_cache_ttl` (default 300s)
- Site statistics: TTL configurable via cache buster logic
- Featured datasets: TTL configurable

## API Actions Available
- `people_list` - User directory with search/filter
- `admin_user_list` - Admin user management with stats
- `organization_people` - Organization member listing
- `get_org_statistics` - Organization dashboard stats

## Implementation Ready
✓ Tracking data fetching (include_tracking=True)
✓ View count display (tracking_summary)
✓ Popularity sorting (views_recent)
✓ Organization statistics
✓ User management tracking
✓ Caching system for performance
