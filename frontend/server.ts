import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import { createServer as createViteServer } from "vite";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

async function startServer() {
  const app = express();
  const PORT = parseInt(process.env.PORT || "3000", 10);

  // Middleware for parsing large image payloads
  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ limit: "50mb", extended: true }));

  // --- API Proxy to FastAPI backend ---
  // All /api/* requests are forwarded to the Python backend.
  app.all("/api/*", async (req, res) => {
    const backendPath = req.originalUrl;
    const targetUrl = `${BACKEND_URL}${backendPath}`;

    try {
      const headers: Record<string, string> = {
        "Content-Type": req.headers["content-type"] || "application/json",
      };

      const fetchOptions: RequestInit = {
        method: req.method,
        headers,
      };

      // Forward body for POST/PUT/PATCH
      if (["POST", "PUT", "PATCH"].includes(req.method) && req.body) {
        fetchOptions.body = JSON.stringify(req.body);
      }

      const backendRes = await fetch(targetUrl, fetchOptions);
      const contentType = backendRes.headers.get("content-type") || "";

      // Forward status code
      res.status(backendRes.status);

      // Forward relevant headers
      if (contentType) res.setHeader("Content-Type", contentType);

      if (contentType.includes("application/json")) {
        const data = await backendRes.json();
        res.json(data);
      } else {
        const text = await backendRes.text();
        res.send(text);
      }
    } catch (err: any) {
      console.error(`[Proxy Error] ${req.method} ${backendPath} ->`, err.message);
      res.status(502).json({
        error: "Backend proxy error",
        detail: err.message,
        hint: `Ensure the FastAPI backend is running at ${BACKEND_URL}`,
      });
    }
  });

  // --- Serve Frontend ---
  if (process.env.NODE_ENV !== "production") {
    // Mount Vite in middleware mode for HMR
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
    console.log("Vite dev middleware mounted.");
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
    console.log("Serving static production assets from dist/.");
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`\n🚀 Frontend server: http://localhost:${PORT}`);
    console.log(`🔗 Backend proxy target: ${BACKEND_URL}`);
    console.log(`   All /api/* requests are forwarded to the FastAPI backend.\n`);
  });
}

startServer();
