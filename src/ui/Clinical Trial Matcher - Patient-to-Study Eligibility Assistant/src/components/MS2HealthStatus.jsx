import React, { useState, useEffect } from "react";

function MS2HealthStatus() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Use environment variable with fallback
  const MS2_HEALTH_URL = import.meta.env.VITE_MS2_HEALTH_URL || "http://localhost:8002/api/ms2/health";

  const checkHealth = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(MS2_HEALTH_URL);
      const data = await response.json();
      setHealth(data);
    } catch (err) {
      setError("Unable to connect to MS2 service");
      console.error("Health check error:", err);
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
    if (health.status === "healthy") return "#28a745"; // Green
    return "#ffc107"; // Yellow
  };

  const getStatusIcon = () => {
    if (loading) return "⏳";
    if (error) return "❌";
    if (health?.status === "healthy") return "✅";
    return "⚠️";
  };

  return (
    <div className="mb-8 p-4 bg-white rounded-lg shadow-md border-l-4" style={{ borderLeftColor: getStatusColor() }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{getStatusIcon()}</span>
          <div>
            <h3 className="font-semibold text-gray-800">MS2 Service Status</h3>
            <p className="text-sm text-gray-600">
              {loading ? "Checking..." : error ? error : `Status: ${health?.status || "unknown"}`}
            </p>
          </div>
        </div>
        <button
          onClick={checkHealth}
          disabled={loading}
          className="px-4 py-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 disabled:bg-gray-100 disabled:text-gray-400 font-semibold text-sm transition-all"
        >
          {loading ? "Checking..." : "Refresh"}
        </button>
      </div>
    </div>
  );
}

export default MS2HealthStatus;
