export interface Product {
  id?: number;
  sku: string;
  nombre: string;
  descripcion: string;
  categoria?: string; // <-- ¡Nueva propiedad! Hazla opcional por si algunos productos no la tienen inicialmente
  precio: number;
  stock: number;
  imagen_url?: string;
  activo?: boolean;
  fecha_creacion?: string;
  fecha_actualizacion?: string;
}