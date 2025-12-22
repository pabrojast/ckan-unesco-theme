/**
 * Responsive Top Menu JavaScript
 * Handles mobile dropdown functionality for the UNESCO theme
 */

document.addEventListener('DOMContentLoaded', function() {
  const toggleButton = document.querySelector('.topmenu-dropdown-toggle');
  const dropdown = document.querySelector('.topmenu-dropdown');
  
  if (toggleButton && dropdown) {
    // Toggle dropdown on click
    toggleButton.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      const isActive = this.classList.contains('active');
      
      if (isActive) {
        this.classList.remove('active');
        dropdown.style.display = 'none';
      } else {
        this.classList.add('active');
        dropdown.style.display = 'block';
      }
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
      if (!toggleButton.contains(e.target) && !dropdown.contains(e.target)) {
        toggleButton.classList.remove('active');
        dropdown.style.display = 'none';
      }
    });
    
    // Close dropdown when window resizes (in case user switches from mobile to desktop)
    window.addEventListener('resize', function() {
      toggleButton.classList.remove('active');
      dropdown.style.display = 'none';
    });
    
    // Handle ESC key to close dropdown
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && toggleButton.classList.contains('active')) {
        toggleButton.classList.remove('active');
        dropdown.style.display = 'none';
        toggleButton.focus(); // Return focus to button for accessibility
      }
    });
  }
});