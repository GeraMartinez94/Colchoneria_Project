// src/app/services/product.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Product } from '../models/product.model';

@Injectable({
  providedIn: 'root'
})
export class ProductService {
  private baseUrl = 'https://colchoneria.onrender.com';
  private apiUrl = '/api/productos';
  private categoriesApiUrl = '/api/categorias';

  constructor(private http: HttpClient) { }

  /**
   * Obtiene una lista de productos desde el backend.
   * Ahora, este método no acepta el parámetro 'categoria' directamente,
   * siempre obtendrá todos los productos.
   * @returns Un Observable que emite un array de objetos Product.
   */
  getProducts(): Observable<Product[]> {
    // Ya no se necesitan HttpParams si no se filtra por categoría aquí
    return this.http.get<Product[]>(this.apiUrl);
  }

  /**
   * Obtiene un producto específico por su ID.
   * @param id El ID del producto.
   * @returns Un Observable con los detalles del producto.
   */
  getProductById(id: number): Observable<Product> {
    const url = `${this.apiUrl}/${id}`; // Construye la URL para el producto específico
    return this.http.get<Product>(url);
  }

  /**
   * Sube un archivo Excel al backend.
   * @param file El archivo Excel a subir.
   * @returns Un Observable que emite la respuesta del backend.
   */
  uploadExcel(file: File): Observable<any> {
    const formData: FormData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<any>('/api/upload-excel', formData);
  }

  /**
   * Elimina todos los productos de la base de datos.
   * @returns Un Observable que emite la respuesta del backend.
   */
  deleteAllProducts(): Observable<any> {
    return this.http.delete<any>(this.apiUrl);
  }

  /**
   * Obtiene una lista de categorías únicas de productos desde el backend.
   * @returns Un Observable que emite un array de strings (nombres de categorías).
   */
  getCategories(): Observable<string[]> {
    return this.http.get<string[]>(this.categoriesApiUrl);
  }
}
