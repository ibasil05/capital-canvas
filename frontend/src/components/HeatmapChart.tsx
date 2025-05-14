import { useEffect, useRef } from 'react';
import { select } from 'd3-selection';
import { scaleBand, scaleSequential } from 'd3-scale';
import { min, max } from 'd3-array';
import { interpolateRdYlBu } from 'd3-scale-chromatic';
import { axisBottom, axisLeft } from 'd3-axis';

interface HeatmapProps {
  data: number[][];
  xLabels: string[];
  yLabels: string[];
  title?: string;
  width?: number;
  height?: number;
}

export function HeatmapChart({ data, xLabels, yLabels, title, width = 600, height = 400 }: HeatmapProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data || !data.length) return;

    // Clear previous content
    select(svgRef.current).selectAll("*").remove();

    const margin = { top: 40, right: 40, bottom: 60, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const svg = select(svgRef.current)
      .attr("width", width)
      .attr("height", height);

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Color scale
    const colorScale = scaleSequential()
      .domain([min(data.flat()) || 0, max(data.flat()) || 0])
      .interpolator(interpolateRdYlBu);

    // Scales
    const xScale = scaleBand()
      .domain(xLabels)
      .range([0, innerWidth])
      .padding(0.05);

    const yScale = scaleBand()
      .domain(yLabels)
      .range([innerHeight, 0])
      .padding(0.05);

    // Create cells
    for (let i = 0; i < data.length; i++) {
      for (let j = 0; j < data[i].length; j++) {
        g.append("rect")
          .attr("x", xScale(xLabels[j]) || 0)
          .attr("y", yScale(yLabels[i]) || 0)
          .attr("width", xScale.bandwidth())
          .attr("height", yScale.bandwidth())
          .attr("fill", colorScale(data[i][j]))
          .append("title")
          .text(`${yLabels[i]}, ${xLabels[j]}: ${data[i][j].toFixed(1)}%`);
      }
    }

    // Add cell values
    for (let i = 0; i < data.length; i++) {
      for (let j = 0; j < data[i].length; j++) {
        g.append("text")
          .attr("x", (xScale(xLabels[j]) || 0) + xScale.bandwidth() / 2)
          .attr("y", (yScale(yLabels[i]) || 0) + yScale.bandwidth() / 2)
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "middle")
          .attr("fill", data[i][j] > 0 ? "#000" : "#fff")
          .style("font-size", "12px")
          .text(`${data[i][j].toFixed(1)}%`);
      }
    }

    // Add axes
    const xAxis = axisBottom(xScale);
    const yAxis = axisLeft(yScale);

    g.append("g")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(xAxis)
      .selectAll("text")
      .style("text-anchor", "end")
      .attr("dx", "-.8em")
      .attr("dy", ".15em")
      .attr("transform", "rotate(-45)");

    g.append("g")
      .call(yAxis);

    // Add title
    if (title) {
      svg.append("text")
        .attr("x", width / 2)
        .attr("y", margin.top / 2)
        .attr("text-anchor", "middle")
        .style("font-size", "16px")
        .text(title);
    }

    // Add axis labels
    svg.append("text")
      .attr("transform", `translate(${width/2},${height-10})`)
      .style("text-anchor", "middle")
      .text("Terminal Growth Rate (%)");

    svg.append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", 15)
      .attr("x", -height/2)
      .style("text-anchor", "middle")
      .text("WACC (%)");

  }, [data, xLabels, yLabels, title, width, height]);

  return <svg ref={svgRef}></svg>;
}
