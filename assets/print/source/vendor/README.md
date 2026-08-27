# Vendored print-pipeline JS

Production UMD builds of React 18.3.1. The print HTML loads these from disk
(`file://`); it does not fetch unpkg or compile JSX in Chrome.

- `react.production.min.js` — https://unpkg.com/react@18.3.1/umd/react.production.min.js
- `react-dom.production.min.js` — https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js

Rebuild the JSX bundle with `node compile-jsx.mjs` after editing any `*.jsx`.
