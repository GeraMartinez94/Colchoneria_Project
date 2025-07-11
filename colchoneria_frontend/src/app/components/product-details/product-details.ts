// src/app/components/product-details/product-details.component.ts
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ProductService } from '../../services/product-service';
import { CommonModule, CurrencyPipe } from '@angular/common';
import { Product } from '../../models/product.model';

@Component({
  selector: 'app-product-details',
  standalone: true,
  imports: [CommonModule, CurrencyPipe],
  templateUrl: './product-details.html',
  styleUrls: ['./product-details.css']
})
export class ProductDetailsComponent implements OnInit {
  product: Product | undefined;
  errorMessage: string = '';
  loading: boolean = true;

  // Formas de pago (ejemplo, puedes expandirlas o traerlas del backend si es necesario)
  paymentMethods: string[] = [
    'Tarjeta de Crédito (Visa, MasterCard, American Express)',
    'Tarjeta de Débito',
    'Transferencia Bancaria',
    'Efectivo'
  ];

  constructor(
    private route: ActivatedRoute,
    private productService: ProductService,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const productId = params.get('id');
      if (productId) {
        this.loadProductDetails(parseInt(productId, 10));
      } else {
        this.errorMessage = 'ID de producto no proporcionado.';
        this.loading = false;
      }
    });
  }

  loadProductDetails(id: number): void {
    this.loading = true;
    this.productService.getProductById(id).subscribe({
      next: (data) => {
        this.product = data;
        this.loading = false;
      },
      error: (error) => {
        console.error('Error al cargar los detalles del producto:', error);
        this.errorMessage = 'No se pudo cargar el producto. Por favor, inténtalo de nuevo más tarde.';
        this.loading = false;
      }
    });
  }

  goBackToList(): void {
    this.router.navigate(['/productos']);
  }
}
