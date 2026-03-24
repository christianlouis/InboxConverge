export async function register() {
  const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
  console.log(`[proxy] BACKEND_URL = ${backendUrl}`);
}
