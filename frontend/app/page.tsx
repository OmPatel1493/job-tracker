import { redirect } from "next/navigation";

// Root route: redirect to login
export default function Home() {
  redirect("/login");
}
