import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { routes } from './app.routes';
import { AuthInterceptor } from './services/auth.interceptor'; // Importa tu interceptor

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
       provideHttpClient(withInterceptorsFromDi()), 
        // Proporciona tu interceptor
        { provide: HTTP_INTERCEPTORS, useClass: AuthInterceptor, multi: true }
  ]
};
