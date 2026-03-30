export type ApiEndpointSection = "generation" | "dsa" | "future";

export interface ApiEndpointMeta {
  id: string;
  path: string;
  method: string;
  label: string;
  description: string;
  implemented: boolean;
  section: ApiEndpointSection;
}
