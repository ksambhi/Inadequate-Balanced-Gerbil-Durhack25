import React, { useState } from 'react';
import type { SeatingPlan, EventSettings, Attendee } from '../../types/data.types';
import styles from './SeatingVisualizer.module.scss';

// --- PROPS INTERFACE ---
interface Props {
  plan: SeatingPlan;
  settings: EventSettings; // Needed to map view names to view array indices
}

// --- COLOR UTILITY FUNCTIONS (Place in a utils file for a cleaner project) ---

// Define your color constants using the imported variables
// src/components/SeatingVisualizer/SeatingVisualizer.tsx

// --- STATIC COLOR PALETTE (Max 10 Topics) ---
// Each object contains the two hex colors that define the extremes (A and B)
// for the gradient of a single view topic.
const TOPIC_COLOR_PALETTE = [
  // Index 0: For the first topic (e.g., 'politics' or 'chocolate')
  { A: '#007bff', B: '#dc3545' }, // Blue vs Red
  
  // Index 1: For the second topic (e.g., 'age')
  { A: '#28a745', B: '#ffc107' }, // Green vs Yellow
  
  // Index 2
  { A: '#6f42c1', B: '#fd7e14' }, // Purple vs Orange
  
  // Index 3
  { A: '#e83e8c', B: '#17a2b8' }, // Pink vs Teal
  
  // Index 4
  { A: '#6c757d', B: '#343a40' }, // Light Gray vs Dark Gray

  // Index 5
  { A: '#40e0d0', B: '#f4a460' }, // Turquoise vs Sandy Brown
  
  // Index 6
  { A: '#800000', B: '#008080' }, // Maroon vs Olive
  
  // Index 7
  { A: '#9acd32', B: '#b22222' }, // Yellow Green vs Fire Brick
  
  // Index 8
  { A: '#00bfff', B: '#ff69b4' }, // Deep Sky Blue vs Hot Pink

  // Index 9 (Last option)
  { A: '#556b2f', B: '#8b008b' }, // Dark Olive Green vs Dark Magenta
];
// ---------------------------------------------

// Converts hex to RGB array [r, g, b]
const hexToRgb = (hex: string): number[] => {
    const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
    hex = hex.replace(shorthandRegex, (m, r, g, b) => r + r + g + g + b + b);
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)!;
    return result ? [
        parseInt(result[1], 16),
        parseInt(result[2], 16),
        parseInt(result[3], 16)
    ] : [0, 0, 0];
};

// Helper function to interpolate between two colors
// NOTE: Factor 0 returns Color 1, Factor 1 returns Color 2
const interpolateColor = (color1: number[], color2: number[], factor: number): string => {
    if (factor <= 0) return `rgb(${color1.join(',')})`;
    if (factor >= 1) return `rgb(${color2.join(',')})`;

    const result = color1.slice();
    for (let i = 0; i < 3; i++) {
        result[i] = Math.round(result[i] + factor * (color2[i] - color1[i]));
    }
    return `rgb(${result.join(',')})`;
};

/**
 * Calculates a gradient color based on a numeric view value (0 to 1).
 * @param viewValue The numeric view value (0 to 1).
 * @param selectedView The current theme ('chocolate', 'age', etc.).
 * @param settings The EventSettings object (REQUIRED to get the view index).
 * @returns A CSS RGB color string.
 */
const getDynamicBackgroundColor = (viewValue: number, selectedView: string, settings: EventSettings): string => {
    // 1. Find the index of the selected view name in the settings array.
    // This index corresponds to the position in TOPIC_COLOR_PALETTE.
    const viewIndex = settings.views.indexOf(selectedView);

    // 2. Look up the color pair using that index.
    const colors = TOPIC_COLOR_PALETTE[viewIndex];

    if (!colors) {
      // If index is -1 (view not found) or outside the palette's range (0-9)
      console.warn(`Color mapping failed for view: ${selectedView}. Using default.`);
      return 'lightgray'; 
    }

    // Color A is the '1' extreme, Color B is the '0' extreme
    const colorARgb = hexToRgb(colors.A);
    const colorBRgb = hexToRgb(colors.B);
    
    // Normalize factor and interpolate from Color B (factor 0) to Color A (factor 1)
    const factor = Math.min(1, Math.max(0, viewValue)); 
    
    return interpolateColor(colorBRgb, colorARgb, factor); 
};

// --- VIEW VALUE RETRIEVAL ---

/**
 * Maps the selected view name to the correct numeric value in the AttendeeViews array.
 */
const getCurrentViewValue = (attendee: Attendee, selectedView: string, settings: EventSettings): number => {
    const viewIndex = settings.views.indexOf(selectedView);
    
    if (viewIndex === -1 || !attendee.opinions.views[viewIndex]) {
        // Fallback to neutral if view not found or index is out of bounds
        return 0.5; 
    }
    
    return attendee.opinions.views[viewIndex]; 
};


export const SeatingVisualizer: React.FC<Props> = ({ plan, settings }) => {
  const [selectedView, setSelectedView] = useState(settings.views[0] || 'chocolate');
  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    attendee: Attendee | null;
  }>({
    visible: false,
    x: 0,
    y: 0,
    attendee: null
  });

  const handleMouseEnter = (e: React.MouseEvent, attendee: Attendee) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({
      visible: true,
      x: rect.left + rect.width / 2,
      y: rect.top - 10,
      attendee
    });
  };

  const handleMouseLeave = () => {
    setTooltip({ visible: false, x: 0, y: 0, attendee: null });
  };

  return (
    <div className={styles.visualizerContainer}>
      <div className={styles.header}>
        <h2>Seating Plan for: {settings.eventName}</h2>
        <p className={styles.description}>
          The plan below shows seating based on the algorithm. Attendee colors reflect their views on the currently selected topic (gradient from **{TOPIC_COLOR_PALETTE.find((_, index) => settings.views[index] === selectedView)?.B || 'Color B'}** to **{TOPIC_COLOR_PALETTE.find((_, index) => settings.views[index] === selectedView)?.A || 'Color A'}**).
        </p>

        <div className={styles.viewSelector}>
          <label htmlFor="view-select">Color by View:</label>
          <select
            id="view-select"
            value={selectedView}
            onChange={(e) => setSelectedView(e.target.value)}
          >
            {settings.views.map((viewName) => (
              <option key={viewName} value={viewName}>
                {viewName.charAt(0).toUpperCase() + viewName.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.seatingLayout}>
        {plan.tables.map((table) => (
          <div key={table.id} className={styles.tableContainer}>
            <div className={styles.table}>
              Table {table.id} ({table.attendees.length} / {table.capacity} Seats)
            </div>
            
            <div className={styles.attendeeGrid}>
              {table.attendees.map((attendee) => {
                  const viewValue = getCurrentViewValue(attendee, selectedView, settings);
                  const dynamicColor = getDynamicBackgroundColor(viewValue, selectedView, settings);
                  
                  return (
                      <div 
                          key={attendee.id} 
                          className={styles.attendeeChip}
                          style={{ backgroundColor: dynamicColor }}
                          onMouseEnter={(e) => handleMouseEnter(e, attendee)}
                          onMouseLeave={handleMouseLeave}
                      >
                          {attendee.name} 
                          <span className={styles.scoreText}>({(viewValue * 100).toFixed(0)}%)</span>
                      </div>
                  );
              })}
              
              {Array(table.capacity - table.attendees.length).fill(0).map((_, index) => (
                <div key={`empty-${table.id}-${index}`} className={styles.emptySeat}>
                    (Empty)
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Tooltip */}
      {tooltip.visible && tooltip.attendee && (
        <div
          className={styles.tooltip}
          style={{
            left: `${tooltip.x}px`,
            top: `${tooltip.y}px`,
            transform: 'translate(-50%, -100%)'
          }}
        >
          <div className={styles.tooltipContent}>
            <h4>{tooltip.attendee.name}</h4>
            <div className={styles.tooltipViews}>
              {settings.views.map((viewName) => {
                const value = getCurrentViewValue(tooltip.attendee!, viewName, settings);
                return (
                  <div key={viewName} className={styles.tooltipRow}>
                    <span className={styles.tooltipLabel}>
                      {viewName.charAt(0).toUpperCase() + viewName.slice(1)}:
                    </span>
                    <span className={styles.tooltipValue}>
                      {(value * 100).toFixed(0)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};