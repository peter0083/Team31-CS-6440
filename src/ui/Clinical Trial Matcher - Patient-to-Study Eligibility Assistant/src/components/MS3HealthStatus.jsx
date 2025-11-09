import React, { useState, useEffect } from "react";

function MS3HealthStatus() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Use environment variable with fallback
  const MS3_HEALTH_URL =
    import.meta.env.VITE_MS3_HEALTH_URL || "http://localhost:8003/live";

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(MS3_HEALTH_URL);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setHealth(data);
    } catch (err) {
      setError("Unable to connect to MS3 service");
      console.error("MS3 health check error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Check health on mount and every 30 seconds
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = () => {
    if (error) return "#dc3545"; // Red
    if (!health) return "#6c757d"; // Gray
    if (health.status === "alive") return "#28a745"; // Green
    return "#ffc107"; // Yellow
  };

  const getStatusIcon = () => {
    if (loading) return "⏳";
    if (error) return "❌";
    if (health?.status === "alive") return "✅";
    return "⚠️";
  };

  return (
    <div
      style={{
        padding: "10px 15px",
        margin: "10px 0",
        borderRadius: "5px",
        backgroundColor: getStatusColor(),
        color: "white",
        fontWeight: "bold",
        fontSize: "14px",
        display: "flex",
        alignItems: "center",
        gap: "8px",
      }}
    >
      <span style={{ fontSize: "18px" }}>{getStatusIcon()}</span>
      <span>
        MS3 Phenotype Builder:{" "}
        {loading ? "Checking..." : error ? error : `Status: ${health?.status || "unknown"}`}
      </span>
    </div>
  );
}

export default MS3HealthStatus;
