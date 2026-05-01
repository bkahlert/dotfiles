# Tailwind & Derivative Libraries (DaisyUI, etc.) Standards

- **Strict Rule: No Dynamic Class Construction**
    - **Never** use string concatenation or template literals to build class names for Tailwind CSS or any based library (DaisyUI, Flowbite, etc.).
    - **Reason**: The Tailwind compiler performs static analysis and only includes classes found as **complete, unbroken strings** in your source code.
      Constructed strings like `` `text-${color}-500` `` will be purged from the production build.
    - **❌ Bad**: `<div className={`alert alert-${type}`}>`
    - **❌ Bad**: `<button className={"btn-" + color}>`
    - **✅ Good**: Use a mapping object or a switch statement to return the **full class name** as a static string.

- **Implementation Pattern (Mapping)**:
  ```javascript
  // The compiler must see the full string (e.g., 'status-success') to include it
  const statusClasses = {
    success: 'status-success',
    error: 'status-error',
    warning: 'status-warning',
  };
  
  const className = `status ${statusClasses[status] || 'status-info'}`;
  ```
