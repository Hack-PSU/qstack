import { useEffect, useRef, useState } from "react";
import { Container, Title, Text, Paper } from "@mantine/core";
import * as d3 from "d3";
import { useUserStore } from "../hooks/useUserStore";

interface Node extends d3.SimulationNodeDatum {
  id: string;
  type: "mentor" | "ticket";
  name: string;
  status?: "open" | "claimed" | "resolved";
  radius: number;
}

interface Link extends d3.SimulationLinkDatum<Node> {
  source: string | Node;
  target: string | Node;
  status: "active" | "resolved";
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

export default function NetworkVisualization() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const loggedIn = useUserStore((store) => store.loggedIn);

  // Fetch tickets and build graph data
  useEffect(() => {
    if (!loggedIn) return;

    const fetchData = async () => {
      try {
        const response = await fetch("/api/queue");
        const data = await response.json();

        const mentorNodes = new Map<string, Node>();
        const ticketNodes: Node[] = [];
        const links: Link[] = [];

        // Process tickets
        data.tickets?.forEach((ticket: any) => {
          // Add ticket node
          ticketNodes.push({
            id: `ticket-${ticket.id}`,
            type: "ticket",
            name: ticket.name || "Anonymous",
            status: ticket.status,
            radius: 8,
          });

          // If ticket is claimed, add mentor node and link
          if (ticket.claim_id && ticket.claim_name) {
            const mentorId = `mentor-${ticket.claim_id}`;

            if (!mentorNodes.has(mentorId)) {
              mentorNodes.set(mentorId, {
                id: mentorId,
                type: "mentor",
                name: ticket.claim_name,
                radius: 12,
              });
            }

            links.push({
              source: mentorId,
              target: `ticket-${ticket.id}`,
              status: ticket.status === "resolved" ? "resolved" : "active",
            });
          }
        });

        setGraphData({
          nodes: [...Array.from(mentorNodes.values()), ...ticketNodes],
          links,
        });
      } catch (error) {
        console.error("Failed to fetch graph data:", error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000); // Refresh every 3 seconds

    return () => clearInterval(interval);
  }, [loggedIn]);

  // D3 visualization
  useEffect(() => {
    if (!svgRef.current || graphData.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Create force simulation
    const simulation = d3
      .forceSimulation<Node>(graphData.nodes)
      .force(
        "link",
        d3.forceLink<Node, Link>(graphData.links).id((d) => d.id).distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d: any) => d.radius + 10));

    // Create gradient for active links
    const defs = svg.append("defs");

    const gradient = defs
      .append("linearGradient")
      .attr("id", "link-gradient-active")
      .attr("gradientUnits", "userSpaceOnUse");

    gradient.append("stop").attr("offset", "0%").attr("stop-color", "#3b82f6");
    gradient.append("stop").attr("offset", "100%").attr("stop-color", "#8b5cf6");

    // Add glow filter for nodes
    const filter = defs.append("filter").attr("id", "glow");
    filter
      .append("feGaussianBlur")
      .attr("stdDeviation", "3")
      .attr("result", "coloredBlur");
    const feMerge = filter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    const g = svg.append("g");

    // Add zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Draw links
    const link = g
      .append("g")
      .selectAll("line")
      .data(graphData.links)
      .join("line")
      .attr("stroke", (d) =>
        d.status === "resolved" ? "#10b981" : "url(#link-gradient-active)"
      )
      .attr("stroke-width", 2)
      .attr("stroke-opacity", (d) => (d.status === "resolved" ? 0.4 : 0.8))
      .attr("class", (d) => d.status === "active" ? "link-pulse" : "");

    // Draw nodes
    const node = g
      .append("g")
      .selectAll("circle")
      .data(graphData.nodes)
      .join("circle")
      .attr("r", (d) => d.radius)
      .attr("fill", (d) => {
        if (d.type === "mentor") return "#8b5cf6"; // Purple for mentors
        if (d.status === "resolved") return "#10b981"; // Green for resolved
        if (d.status === "claimed") return "#f59e0b"; // Orange for claimed
        return "#3b82f6"; // Blue for open
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .attr("filter", (d) => (d.type === "mentor" ? "url(#glow)" : "none"))
      .style("cursor", "pointer");

    // Add labels
    const label = g
      .append("g")
      .selectAll("text")
      .data(graphData.nodes)
      .join("text")
      .text((d) => d.name)
      .attr("font-size", (d) => (d.type === "mentor" ? "14px" : "12px"))
      .attr("font-weight", (d) => (d.type === "mentor" ? "bold" : "normal"))
      .attr("fill", "#fff")
      .attr("text-anchor", "middle")
      .attr("dy", (d) => d.radius + 15)
      .style("pointer-events", "none");

    // Drag behavior
    const drag = d3
      .drag<SVGCircleElement, Node>()
      .on("start", (event) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      })
      .on("drag", (event) => {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      })
      .on("end", (event) => {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      });

    node.call(drag);

    // Update positions on tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node.attr("cx", (d) => d.x!).attr("cy", (d) => d.y!);

      label.attr("x", (d) => d.x!).attr("y", (d) => d.y!);
    });

    return () => {
      simulation.stop();
    };
  }, [graphData]);

  if (!loggedIn) {
    return (
      <Container size="sm" py="6rem">
        <Paper p="xl" shadow="xs" className="bg-neutral-800">
          <Title order={2} ta="center" mb="md">
            Network Visualization
          </Title>
          <Text ta="center" c="dimmed">
            Please log in to view the live mentor network.
          </Text>
        </Paper>
      </Container>
    );
  }

  return (
    <div style={{ width: "100vw", height: "100vh", background: "#0a0a0a" }}>
      <div style={{ position: "absolute", top: 20, left: 20, zIndex: 10 }}>
        <Paper p="md" shadow="xs" className="bg-neutral-800" style={{ background: "rgba(23, 23, 23, 0.9)" }}>
          <Title order={3} mb="xs">
            Live Mentor Network
          </Title>
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  background: "#8b5cf6",
                }}
              />
              <Text size="sm">Mentors</Text>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  background: "#3b82f6",
                }}
              />
              <Text size="sm">Open Tickets</Text>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  background: "#f59e0b",
                }}
              />
              <Text size="sm">Claimed</Text>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div
                style={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  background: "#10b981",
                }}
              />
              <Text size="sm">Resolved</Text>
            </div>
          </div>
        </Paper>
      </div>

      <svg
        ref={svgRef}
        style={{
          width: "100%",
          height: "100%",
          background: "#0a0a0a",
        }}
      />

      <style>{`
        @keyframes pulse {
          0%, 100% {
            stroke-opacity: 0.8;
            stroke-width: 2px;
          }
          50% {
            stroke-opacity: 1;
            stroke-width: 3px;
          }
        }

        .link-pulse {
          animation: pulse 2s ease-in-out infinite;
        }

        circle {
          transition: filter 0.3s ease;
        }

        circle:hover {
          filter: brightness(1.2) url(#glow);
        }
      `}</style>
    </div>
  );
}
