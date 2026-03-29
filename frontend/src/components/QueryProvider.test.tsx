import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryProvider } from './QueryProvider';

describe('QueryProvider', () => {
  it('should render children', () => {
    render(
      <QueryProvider>
        <div data-testid="child">Hello</div>
      </QueryProvider>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('should render multiple children', () => {
    render(
      <QueryProvider>
        <div data-testid="first">First</div>
        <div data-testid="second">Second</div>
      </QueryProvider>
    );
    expect(screen.getByTestId('first')).toBeInTheDocument();
    expect(screen.getByTestId('second')).toBeInTheDocument();
  });
});
