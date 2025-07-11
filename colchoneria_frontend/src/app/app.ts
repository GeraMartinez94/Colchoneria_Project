import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterOutlet,RouterLink, Router } from '@angular/router';
import { ProductService } from './services/product-service';
import { Subscription } from 'rxjs';
import { AuthService } from './services/auth';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet,  
     RouterLink,
    CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
title = 'El Galpón Colchonería';
  categories: string[] = [];
  currentYear: number;

  // Propiedades para el estado de autenticación
  isAuthenticated: boolean = false;
  isAdmin: boolean = false;
  username: string | null = null;

  private authSubscription: Subscription = new Subscription(); // Para gestionar las suscripciones

  constructor(
    private productService: ProductService,
    private authService: AuthService, // Inyecta AuthService
    private router: Router // Inyecta Router
  ) {
    this.currentYear = new Date().getFullYear();
  }

  ngOnInit(): void {
    // Suscribirse a los cambios de estado de autenticación
    this.authSubscription.add(
      this.authService.isAuthenticated$.subscribe(status => {
        this.isAuthenticated = status;
      })
    );
    this.authSubscription.add(
      this.authService.isAdmin$.subscribe(status => {
        this.isAdmin = status;
      })
    );
    this.authSubscription.add(
      this.authService.username$.subscribe(name => {
        this.username = name;
      })
    );

    // No necesitamos cargar categorías si no hay menú desplegable de categorías
    // this.loadCategories(); 
  }

  // Método para cerrar sesión
  onLogout(): void {
    this.authService.logout().subscribe({
      next: (response) => {
        console.log('Sesión cerrada:', response.message);
        this.router.navigate(['/productos']); // Redirigir a productos después de cerrar sesión
      },
      error: (error) => {
        console.error('Error al cerrar sesión:', error);
        // Manejar el error, quizás mostrar un mensaje al usuario
      }
    });
  }

  // Importante: Desuscribirse para evitar fugas de memoria
  ngOnDestroy(): void {
    this.authSubscription.unsubscribe();
  }

  // Este método ya no es necesario si eliminamos el menú de categorías
  loadCategories(): void {
    // Si aún necesitas cargar categorías para otros fines, mantenlo.
    // Si no, puedes eliminarlo.
    this.productService.getCategories().subscribe({
      next: (data) => {
        this.categories = data;
        console.log('Categorías cargadas en el frontend:', this.categories);
      },
      error: (error) => {
        console.error('Error al cargar categorías en el frontend:', error);
      }
    });
  }
}
