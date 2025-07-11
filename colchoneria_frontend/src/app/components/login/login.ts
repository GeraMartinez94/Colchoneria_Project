import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-login',
   standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class LoginComponent {
 username = '';
  password = '';
  errorMessage = '';constructor(private authService: AuthService, private router: Router) { }

  onLogin(): void {
    this.errorMessage = ''; // Limpiar mensajes de error anteriores

    if (!this.username || !this.password) {
      this.errorMessage = 'Por favor, ingresa tu nombre de usuario y contraseña.';
      return;
    }

    this.authService.login(this.username, this.password).subscribe({
      next: (response) => {
        console.log('Inicio de sesión exitoso:', response);
        // Redirigir al usuario a la página de productos (o a donde desees)
        this.router.navigate(['/productos']); 
      },
      error: (error) => {
        console.error('Error de inicio de sesión:', error);
        this.errorMessage = error.error?.message || 'Error al iniciar sesión. Verifica tus credenciales.';
      }
    });
  }
}
