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
    width: rem(32),
    height: rem(32),
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  // Make icon larger
  icon: {
    fontSize: rem(18)
  }
};
