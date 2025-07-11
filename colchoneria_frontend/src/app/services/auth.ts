// src/app/services/auth.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, tap } from 'rxjs'; // Importa BehaviorSubject y tap

interface AuthResponse {
  message: string;
  user?: {
    username: string;
    is_admin: boolean;
  };
}

interface SessionStatus {
  is_authenticated: boolean;
  username?: string;
  is_admin?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private baseUrl = 'https://colchoneria-backend.onrender.com'; 
  private loginUrl = `${this.baseUrl}/api/login`; // <-- ¡CORRECCIÓN AQUÍ!
  private logoutUrl = `${this.baseUrl}/logout`; // <-- ¡CORRECCIÓN AQUÍ!
  private sessionStatusUrl = `${this.baseUrl}/api/session_status`;
  // BehaviorSubject para mantener el estado de autenticación y el rol
  // Lo inicializamos con un estado no autenticado por defecto
  private _isAuthenticated = new BehaviorSubject<boolean>(false);
  private _isAdmin = new BehaviorSubject<boolean>(false);
  private _username = new BehaviorSubject<string | null>(null);

  // Observables públicos para que los componentes puedan suscribirse
  isAuthenticated$ = this._isAuthenticated.asObservable();
  isAdmin$ = this._isAdmin.asObservable();
  username$ = this._username.asObservable();

  constructor(private http: HttpClient) {
    // Al iniciar el servicio, verificamos el estado de la sesión con el backend
    this.checkSessionStatus().subscribe();
  }

  /**
   * Realiza la petición de inicio de sesión al backend.
   * @param username Nombre de usuario.
   * @param password Contraseña.
   * @returns Observable con la respuesta de autenticación.
   */
  login(username: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(this.loginUrl, { username, password }).pipe(
      tap(response => {
        if (response.user) {
          this._isAuthenticated.next(true);
          this._isAdmin.next(response.user.is_admin);
          this._username.next(response.user.username);
          // Opcional: guardar el estado en localStorage para persistencia básica
          localStorage.setItem('is_authenticated', 'true');
          localStorage.setItem('is_admin', response.user.is_admin.toString());
          localStorage.setItem('username', response.user.username);
        }
      })
    );
  }

  /**
   * Realiza la petición de cierre de sesión al backend.
   * @returns Observable con la respuesta de cierre de sesión.
   */
  logout(): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(this.logoutUrl, {}).pipe(
      tap(() => {
        this._isAuthenticated.next(false);
        this._isAdmin.next(false);
        this._username.next(null);
        // Limpiar localStorage
        localStorage.removeItem('is_authenticated');
        localStorage.removeItem('is_admin');
        localStorage.removeItem('username');
      })
    );
  }

  /**
   * Verifica el estado de la sesión actual con el backend.
   * @returns Observable con el estado de la sesión.
   */
  checkSessionStatus(): Observable<SessionStatus> {
    return this.http.get<SessionStatus>(this.sessionStatusUrl).pipe(
      tap(status => {
        this._isAuthenticated.next(status.is_authenticated);
        this._isAdmin.next(status.is_admin || false); // Asegura que sea false si no está presente
        this._username.next(status.username || null);
        // Sincronizar con localStorage si el estado del backend es diferente
        if (status.is_authenticated) {
            localStorage.setItem('is_authenticated', 'true');
            localStorage.setItem('is_admin', (status.is_admin || false).toString());
            localStorage.setItem('username', status.username || '');
        } else {
            localStorage.removeItem('is_authenticated');
            localStorage.removeItem('is_admin');
            localStorage.removeItem('username');
        }
      })
    );
  }

  // Métodos getter para el estado actual (síncronos)
  get isAuthenticated(): boolean {
    return this._isAuthenticated.value;
  }

  get isAdmin(): boolean {
    return this._isAdmin.value;
  }

  get username(): string | null {
    return this._username.value;
  }
}
