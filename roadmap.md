Layout Module

All the below-mentioned libraries are already installed. If anything is not mentioned, please mention it in the chat. Do not load libraries/CDNs in the code. 

Models:
1. Layout (already exists)
2. LayoutBlock (already exists)
3. LayoutFilterConfig (already exists)

Pages:
layouts/ → Layout List (list of user’s layouts; create new)
  - It should inherit the base.html template
  - A simple table view showing all layouts owned by the user a(Private first, then public)
  - Each row should have: "View", "Edit", "Delete" actions corresponding to the layout.
  - On top of the page, add a button to create a "New Layout"

layouts/create/ → Layout Create (form to create new layout).
  - It should inherit the base.html template
  - Form with Layout model fields. Use crispy forms 
  - If the user is admin/staff, allow the user to set the layout as public/private. For all other users, default to private only.
  - On successful creation, redirect to the Layout Edit page.

layouts/<str:username>/<slug:slug>/edit
  - It should inherit the base.html template
   - This page is for editing all aspects of the layout (metadata + design)
   - Section 1: Layout Metadata Form
     - Form with Layout model fields. Use crispy forms
   - Section 2: A dropdown of available blocks (Format: App > Block Name) to add to the layout.
   - Section 3: Layout Design
     - HTMX-driven grid of blocks with drag/drop/resize/delete functionality. Use Gridstack.js for the grid.
     - Each block should simply be a reflection of the actual block (use HTMX to load the block partials). Nothing less, nothing more. Place the "Delete Button" just above the block settings row.
     - By default, keep a 15px gap between blocks (rows and columns)
     - Each user should have the possibility to set default settings/filters per block and must be saved in LayoutBlock model. These can be different from the block defaults. Even when a user adds the same block twice, they can have different settings. 
     - The saving must be AJAX (no save button). 

layouts/<str:username>/<slug:slug> → Layout Detail (HTMX-driven grid of blocks with sidebar offcanvas for filters).
  - It should inherit the base.html template
  - Section 1:
    - Left: Layout title
    - Right: "Edit" and "Delete" button.
      - For public layouts, only admin/staff users can see the "Edit" and "Delete" buttons.
      - For private layouts, only the owner can see the "Edit" and "Delete" buttons.
      - For "Delete", show a confirmation modal before proceeding.
      - On clicking "Edit", redirect to the Layout Edit page.
      
  - Section 2: 
    - Left: Layout Filters accordion (driven by layout’s filter schema). See "Layout Filters" section below for details.
    - Right: Layout Filter dropdown + Manage + Reset buttons.
      - Layout Filter dropdown: shows saved filter configs (private first, then public). Highlight the active one. Show badges for active filters.
      - Manage: redirects to the Layout Filter Config Manage page (see "Layout Filters" section below for details).
      - Reset: resets to default filter config.

  - Section 3:
    - The blocks itself. It should be placed as described in edit-layout page

Layout Filters
    - layouts/<str:username>/<slug:slug>/filters/manage → Layout Filter Config Manage (list/create/edit/delete saved filter configs).
    - Copy the same logic/template as blocks/manage-filters/<slug:slug> except that it should be for LayoutFilterConfig model.
    - "Filter Layouts" feature is not required for layouts
    - The filter fields for layouts should be dynamically generated based on the block filters.