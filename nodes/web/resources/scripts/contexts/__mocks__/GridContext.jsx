import React, { createContext, useContext } from 'react';

// Create the mock context
const GridContext = createContext(null);

// Create a mock provider component
export function GridProvider({ children, initialEditable = false }) {
  // Mock grid context values and functions
  const mockValue = {
    layout: [],
    isEditable: initialEditable,
    widgetsState: {},
    backendSynced: true,
    backendInitialized: true,
    gridLayoutRef: { current: null },
    toggleGridEditing: jest.fn(() => {
      mockValue.isEditable = !mockValue.isEditable;
    }),
    addWidget: jest.fn((type, config = {}) => `widget-mock-${Date.now()}`),
    removeWidget: jest.fn((widgetId) => {}),
    onLayoutChange: jest.fn((newLayout) => {}),
    initializeGrid: jest.fn((savedState) => {}),
    saveWidgetsState: jest.fn((state) => {}),
    saveToLocalStorage: jest.fn((state) => {}),
    resetGridLayout: jest.fn(() => {}),
    updateWidgetProps: jest.fn((widgetId, newProps) => {})
  };

  return (
    <GridContext.Provider value={mockValue}>
      {children}
    </GridContext.Provider>
  );
}

// Custom hook for using the grid context
export function useGridContext() {
  const context = useContext(GridContext);
  if (!context) {
    throw new Error('useGridContext must be used within a GridProvider');
  }
  return context;
}

// Export mock storage key
export const STORAGE_KEY = 'wall-e-dora-grid-layout-test';