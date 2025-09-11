/**
 * Script to apply the new status icon styles to all status components.
 * 
 * Usage:
 * 1. Run this script to create a modified version of each status component
 * 2. Review and test the changes
 * 3. Replace the original files with the modified versions
 */

const fs = require('fs');
const path = require('path');

// List of all status components except ConnectionStatus and DoorStatus (already updated)
const statusComponents = [
  'GamepadStatus.jsx',
  'PowerStatus.jsx',
  'ServoStatus.jsx'
];

// Get the current directory
const currentDir = __dirname;

statusComponents.forEach(component => {
  const componentPath = path.join(currentDir, component);
  
  // Read the component file
  fs.readFile(componentPath, 'utf8', (err, data) => {
    if (err) {
      console.error(`Error reading ${component}:`, err);
      return;
    }
    
    // Add import for StatusIconStyles
    let modifiedContent = data.replace(
      /import React.*?;/s,
      match => `${match}\nimport { statusIconStyles } from './StatusIconStyles';`
    );
    
    // Find and modify ActionIcon components
    modifiedContent = modifiedContent.replace(
      /<ActionIcon[^>]*>/g,
      match => {
        if (match.includes('style={')) {
          return match.replace(
            /style={\s*([^}]*)\s*}/,
            'style={{ ...statusIconStyles.actionIcon, $1 }}'
          );
        } else {
          return match.replace('>', ' style={statusIconStyles.actionIcon}>');
        }
      }
    );
    
    // Find and modify icon styles
    modifiedContent = modifiedContent.replace(
      /<i[^>]*style={\s*([^}]*)\s*}/g,
      match => {
        return match.replace(
          /style={\s*([^}]*)\s*}/,
          'style={{ $1, ...statusIconStyles.icon }}'
        );
      }
    );
    
    // Write the modified file
    const modifiedFilePath = path.join(currentDir, `${component}.modified`);
    fs.writeFile(modifiedFilePath, modifiedContent, err => {
      if (err) {
        console.error(`Error writing modified ${component}:`, err);
        return;
      }
      console.log(`Modified version of ${component} saved to ${modifiedFilePath}`);
    });
  });
});

console.log('Review the .modified files and manually update each component as needed.');