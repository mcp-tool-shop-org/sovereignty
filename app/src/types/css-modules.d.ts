// Type declarations for CSS modules — Vite-handled, not ts-checked.
declare module "*.module.css" {
  const classes: { readonly [key: string]: string };
  export default classes;
}
