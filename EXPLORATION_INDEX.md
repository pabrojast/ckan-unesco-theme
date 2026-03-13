# CKAN UNESCO Theme Extension - Exploration Index

This directory contains a thorough analysis of the CKAN UNESCO theme extension. Use this index to navigate the documentation.

## 📚 Documentation Files

### 1. **CKAN_EXTENSION_EXPLORATION.md** (22 KB) - MAIN REFERENCE
The comprehensive exploration report containing:
- Full directory structure
- Complete tracking/analytics functionality analysis
- Template structure for datasets and resources
- Helper function registration (20 helpers)
- All actions (31 custom actions)
- Controller functions and views
- CKAN tracking feature integration
- Database models
- **Best for**: Understanding the complete architecture

### 2. **TRACKING_QUICK_REFERENCE.md** (2.6 KB) - QUICK LOOKUP
Fast reference guide with:
- Current tracking integration status
- Custom tracking models (MembershipRequest, BugTicket, FeaturedPublication)
- Statistics helpers summary
- Key files table
- Template locations
- Cache configuration
- API actions available
- **Best for**: Quick lookups while implementing

### 3. **CODE_SNIPPETS.md** (13 KB) - CODE EXAMPLES
10 key code snippets showing:
1. Tracking data in controller (include_tracking=True)
2. Display resource views (tracking_summary)
3. Popularity sort in search (views_recent)
4. Organization statistics
5. Site statistics
6. Helper registration
7. Site statistics display template
8. People directory with filtering
9. Admin user management
10. Resource pagination
- **Best for**: Copy-paste code examples and understanding implementation patterns

### 4. **DOCUMENTATION_INDEX.md** (9.9 KB)
Index of all documentation and previous investigation summaries

### 5. **INVESTIGATION_SUMMARY.md** (9.6 KB)
Previous investigation notes on extension features

### 6. **USER_MANAGEMENT_ANALYSIS.md** (26 KB)
Detailed analysis of user management features
- People & Organizations module
- User profiles with extended fields
- Membership request system
- **Best for**: Understanding user management architecture

### 7. **USER_MANAGEMENT_QUICK_REFERENCE.md** (11 KB)
Quick reference for user management
- Action functions summary
- Helper functions
- Template locations
- Database models

## 🎯 Quick Navigation by Topic

### Understanding Tracking
- See: **TRACKING_QUICK_REFERENCE.md** → "Current Tracking Integration"
- See: **CODE_SNIPPETS.md** → Snippets #1-3
- See: **CKAN_EXTENSION_EXPLORATION.md** → Section 9

### Implementing Analytics
- See: **CKAN_EXTENSION_EXPLORATION.md** → Section 2 (Existing tracking/analytics)
- See: **CODE_SNIPPETS.md** → Snippets #4-7 (Statistics functions)
- See: **TRACKING_QUICK_REFERENCE.md** → "Statistics Helpers"

### Working with Templates
- See: **CKAN_EXTENSION_EXPLORATION.md** → Sections 3-4 (Template structure)
- See: **CODE_SNIPPETS.md** → Snippet #7 (Template examples)
- File paths: See **CKAN_EXTENSION_EXPLORATION.md** → File Paths Summary table

### Using API Actions
- See: **CODE_SNIPPETS.md** → Snippets #8-9 (People and Admin APIs)
- See: **CKAN_EXTENSION_EXPLORATION.md** → Section 8 (Actions details)
- See: **TRACKING_QUICK_REFERENCE.md** → "API Actions Available"

### Database Models
- See: **CKAN_EXTENSION_EXPLORATION.md** → Section 12 (Models)
- See: **USER_MANAGEMENT_ANALYSIS.md** (for user-related models)

### Caching System
- See: **CKAN_EXTENSION_EXPLORATION.md** → Plugin section
- See: **TRACKING_QUICK_REFERENCE.md** → "Cache Configuration"

## 📊 Key Statistics

### Extension Size
- **Main plugin**: 1006 lines
- **Controllers**: 1907 lines  
- **Helpers**: 335 lines
- **Actions**: 1108 lines
- **Templates**: 103 HTML files
- **Total helpers**: 20 registered
- **Total actions**: 31 custom actions
- **Total models**: 3 custom database models

### Tracking Points Found
- ✓ 1 resource view tracking reference
- ✓ 1 popularity sort reference
- ✓ 1 conditional tracking display
- ✓ 3 statistics functions
- ✓ 3 custom tracking models
- ✓ 15+ analytics helper functions

## 🔍 Search Tips

Use Ctrl+F to search within documents:

| Topic | Search | Document |
|-------|--------|----------|
| Tracking | "include_tracking" | CKAN_EXTENSION_EXPLORATION.md, CODE_SNIPPETS.md |
| Views | "tracking_summary" | TRACKING_QUICK_REFERENCE.md, CODE_SNIPPETS.md |
| Statistics | "get_org_statistics" | CKAN_EXTENSION_EXPLORATION.md, CODE_SNIPPETS.md |
| People | "people_list" | CODE_SNIPPETS.md, CKAN_EXTENSION_EXPLORATION.md |
| Cache | "TTL\|cache" | TRACKING_QUICK_REFERENCE.md, CKAN_EXTENSION_EXPLORATION.md |
| Actions | "@toolkit" | CKAN_EXTENSION_EXPLORATION.md, CODE_SNIPPETS.md |
| Templates | "{% set" | CODE_SNIPPETS.md, CKAN_EXTENSION_EXPLORATION.md |

## 🗂️ File Locations

| Component | Path |
|-----------|------|
| Main plugin | `ckanext/theme_ejemplo/plugin.py` |
| Controllers | `ckanext/theme_ejemplo/controller.py` |
| Helpers | `ckanext/theme_ejemplo/helpers.py` |
| Actions | `ckanext/theme_ejemplo/actions.py` |
| Models | `ckanext/theme_ejemplo/model.py` |
| Dataset search | `ckanext/theme_ejemplo/templates/package/search.html` |
| Resource display | `ckanext/theme_ejemplo/templates/package/snippets/resource_item.html` |
| Site stats | `ckanext/theme_ejemplo/templates/home/snippets/stats.html` |
| Organization | `ckanext/theme_ejemplo/templates/organization/` |

## ✅ Checklist for Implementation

Use this checklist when implementing analytics features:

### Phase 1: Understanding
- [ ] Read TRACKING_QUICK_REFERENCE.md
- [ ] Review CODE_SNIPPETS.md sections 1-3
- [ ] Understand current tracking integration

### Phase 2: Infrastructure
- [ ] Review CKAN_EXTENSION_EXPLORATION.md Section 2
- [ ] Examine caching system (Section 10)
- [ ] Check database models (Section 12)

### Phase 3: Implementation
- [ ] Copy relevant code snippets from CODE_SNIPPETS.md
- [ ] Register new helpers in plugin.py
- [ ] Create new actions in actions.py
- [ ] Add templates in templates/

### Phase 4: Testing
- [ ] Test API actions
- [ ] Test template rendering
- [ ] Verify caching behavior
- [ ] Check tracking data collection

## 📝 Notes

- All paths are absolute (starting from `/home/pabrojast/Proyectos/ckan-unesco-theme/`)
- Code snippets include full examples and context
- Statistics functions use configurable caching
- People directory supports advanced filtering
- 31 custom actions available for API extension

## 🔗 Related Documentation

- README.md - Project overview
- CLAUDE.md - Claude AI configuration
- USER_MANAGEMENT_ANALYSIS.md - User module details

---

**Last Updated**: March 13, 2024  
**Explorer**: Codebase Analysis Agent  
**Status**: ✅ Complete Analysis
