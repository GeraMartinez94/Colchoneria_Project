// src/app/components/product-list/product-list.component.ts
import { Component, OnInit } from '@angular/core';
import { ProductService } from '../../services/product-service';
import { Product } from '../../models/product.model'; // <-- Asegúrate de que esta importación sea correcta
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-product-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './product-list.html',
  styleUrls: ['./product-list.css']
})
export class ProductListComponent implements OnInit {
  products: Product[] = [];
  errorMessage: string = '';
  successMessage: string = '';

  constructor(private productService: ProductService) { }

  ngOnInit(): void {
    this.loadProducts(); // Llama a la función para cargar todos los productos
  }

  // Carga todos los productos desde el backend (sin filtro de categoría aquí)
  loadProducts(): void { // <-- Este método no toma argumentos
    this.errorMessage = '';
    this.productService.getProducts().subscribe({ // <-- Llamada a getProducts sin argumentos
      next: (data) => {
        this.products = data;
        if (this.products.length === 0 && !this.successMessage) {
            this.successMessage = '';
        }
      },
      error: (error) => {
        console.error('Error al cargar productos:', error);
        this.errorMessage = 'No se pudieron cargar los productos. Asegúrate de que el backend esté funcionando.';
        this.products = [];
        this.successMessage = '';
      }
    });
  }

  // Función para eliminar todos los productos
  onDeleteAllProducts(): void {
    if (confirm('¿Estás seguro de que quieres eliminar TODOS los productos? Esta acción no se puede deshacer.')) {
      this.productService.deleteAllProducts().subscribe({
        next: (response) => {
          this.successMessage = response.message;
          this.errorMessage = '';
          this.loadProducts();
        },
        error: (error) => {
          console.error('Error al eliminar productos:', error);
          this.errorMessage = error.error?.message || 'Error al eliminar los productos.';
          this.successMessage = '';
        }
      });
    }
  }
}
