# Mantine UI Installation Instructions for WALL-E-DORA

To add Mantine UI to the project, you need to install the following packages:

```bash
pnpm add @mantine/core @mantine/hooks @emotion/react @tabler/icons-react
```

## What's Included

1. **@mantine/core** - The main UI component library
2. **@mantine/hooks** - Useful React hooks (like useDisclosure)
3. **@emotion/react** - Styling engine used by Mantine
4. **@tabler/icons-react** - High quality icon library that works well with Mantine

## How to Install

Run the following command in the project root:

```bash
cd nodes/web/resources && pnpm add @mantine/core @mantine/hooks @emotion/react @tabler/icons-react
```

## Using Mantine UI

The ServoDebug.jsx file has been refactored to use Mantine UI. The key features include:

1. A custom amber theme that matches the project's color scheme
2. Improved responsive layout with Mantine's Grid system
3. Modern form controls with validation
4. Better notifications system
5. Intuitive UI components for better user experience

## Next Steps

After installing the dependencies:

1. Run `make web/build` to rebuild the web resources
2. Refresh the application to see the updated ServoDebug view
3. Consider migrating other components to Mantine UI for consistency

## Note

The ServoDebug component now includes a MantineProvider with a custom theme. If you plan to use Mantine throughout the app, consider:

1. Moving the MantineProvider to App.jsx 
2. Creating a shared theme file in a separate location (e.g., scripts/theme.js)
3. Applying the theme consistently across all components