    // src/app/services/auth.interceptor.ts
    import { Injectable } from '@angular/core';
    import {
      HttpRequest,
      HttpHandler,
      HttpEvent,
      HttpInterceptor,
      HttpErrorResponse
    } from '@angular/common/http';
    import { Observable, throwError } from 'rxjs';
    import { catchError } from 'rxjs/operators';
    import { Router } from '@angular/router';

    @Injectable()
    export class AuthInterceptor implements HttpInterceptor {

      constructor(private router: Router) {}

      intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
        return next.handle(request).pipe(
          catchError((error: HttpErrorResponse) => {
            // Si la respuesta es 401 Unauthorized
            if (error.status === 401) {
              // Redirige al usuario a la página de login de Angular
              // Asegúrate de que '/login' sea la ruta correcta a tu componente de login en Angular
              this.router.navigate(['/login']); 
              console.error('Redirigiendo a login debido a 401 Unauthorized desde el interceptor.');
            }
            // Re-lanza el error para que otros manejadores de errores o el componente lo capturen
            return throwError(() => error);
          })
        );
      }
    }
    