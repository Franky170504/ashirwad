export default function FormMessage({ text, kind = "error" }: { text?: string; kind?: "error" | "success" }) {
  if (!text) return null;
  const color = kind === "error" ? "bg-red-50 text-red-800" : "bg-green-50 text-green-800";
  return <p role={kind === "error" ? "alert" : "status"} className={`rounded-sm px-3 py-2 text-sm ${color}`}>{text}</p>;
}
