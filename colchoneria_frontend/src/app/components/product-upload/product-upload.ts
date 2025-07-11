import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProductService } from '../../services/product-service';
import { Router } from '@angular/router';
@Component({
  selector: 'app-product-upload',
    standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './product-upload.html',
  styleUrl: './product-upload.css'
})
export class ProductUpload  {
  selectedFile: File | null = null;
  uploadMessage: string = '';
  errorMessage: string = '';
  isLoading: boolean = false; // <-- ¡Nueva variable para el estado de carga!

  // Inyecta el servicio Router en el constructor
  constructor(private productService: ProductService, private router: Router) { }

  onFileSelected(event: any): void {
    this.selectedFile = event.target.files[0] as File;
    this.uploadMessage = '';
    this.errorMessage = '';
  }

  onUpload(): void {
    if (!this.selectedFile) {
      this.errorMessage = 'Por favor, selecciona un archivo Excel.';
      return;
    }

    this.isLoading = true; // <-- Activa el estado de carga
    this.uploadMessage = 'Subiendo archivo... Por favor espera.'; // Mensaje de espera
    this.errorMessage = ''; // Limpiar errores anteriores

    this.productService.uploadExcel(this.selectedFile).subscribe({
      next: (response) => {
        this.isLoading = false; // <-- Desactiva el estado de carga
        this.uploadMessage = response.message || 'Archivo cargado correctamente.';
        if (response.errors && response.errors.length > 0) {
            this.errorMessage = 'Algunas filas tuvieron errores: ' + response.errors.join('; ');
        } else {
            this.errorMessage = ''; // Limpiar errores si no hubo
        }
        this.selectedFile = null; // Limpiar selección de archivo

        // Redirige al componente principal (listado de productos) después de un breve retraso
        setTimeout(() => {
          this.router.navigate(['/productos']); // <-- ¡Redirección!
        }, 2000); // Espera 2 segundos para que el usuario vea el mensaje de éxito
      },
      error: (error) => {
        this.isLoading = false; // <-- Desactiva el estado de carga
        console.error('Error al subir el archivo:', error);
        this.uploadMessage = ''; // Limpiar mensaje de subida
        this.errorMessage = error.error?.message || 'Error al subir el archivo Excel. Asegúrate de que el backend esté funcionando y el formato sea correcto.';
      }
    });
  }
}