/**
 * StatusIconStyles Component
 * 
 * Provides consistent styling for status icons in the header.
 * Makes icons larger and more touch-friendly.
 */
import { rem } from '@mantine/core';

export const statusIconStyles = {
  // Make ActionIcon larger and more touch-friendly
  actionIcon: {
    width: rem(36),    // 50% larger than default
    height: rem(36),   // 50% larger than default
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  // Make icon larger
  icon: {
    fontSize: rem(20)  // 50% larger than default
  }
};