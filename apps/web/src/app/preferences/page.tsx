import { redirect } from "next/navigation";

export default function PreferencesRedirectPage() {
  redirect("/profile#preferences");
}
