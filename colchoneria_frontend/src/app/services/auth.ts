    // src/app/services/auth.service.ts
    import { Injectable } from '@angular/core';
    import { HttpClient } from '@angular/common/http';
    import { Observable, BehaviorSubject, tap } from 'rxjs';

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
      // ¡IMPORTANTE! Esta es la URL de tu backend desplegado en Render
      private baseUrl = 'https://colchoneria-backend.onrender.com'; 
      private loginUrl = `${this.baseUrl}/api/login`; // <-- Debe usar baseUrl
      private logoutUrl = `${this.baseUrl}/logout`; // <-- Debe usar baseUrl
      private sessionStatusUrl = `${this.baseUrl}/api/session_status`; // <-- Debe usar baseUrl

      private _isAuthenticated = new BehaviorSubject<boolean>(false);
      private _isAdmin = new BehaviorSubject<boolean>(false);
      private _username = new BehaviorSubject<string | null>(null);

      isAuthenticated$ = this._isAuthenticated.asObservable();
      isAdmin$ = this._isAdmin.asObservable();
      username$ = this._username.asObservable();

      constructor(private http: HttpClient) {
        this.checkSessionStatus().subscribe();
      }

      login(username: string, password: string): Observable<AuthResponse> {
        return this.http.post<AuthResponse>(this.loginUrl, { username, password }).pipe(
          tap(response => {
            if (response.user) {
              this._isAuthenticated.next(true);
              this._isAdmin.next(response.user.is_admin);
              this._username.next(response.user.username);
              localStorage.setItem('is_authenticated', 'true');
              localStorage.setItem('is_admin', response.user.is_admin.toString());
              localStorage.setItem('username', response.user.username);
            }
          })
        );
      }

      logout(): Observable<AuthResponse> {
        return this.http.post<AuthResponse>(this.logoutUrl, {}).pipe(
          tap(() => {
            this._isAuthenticated.next(false);
            this._isAdmin.next(false);
            this._username.next(null);
            localStorage.removeItem('is_authenticated');
            localStorage.removeItem('is_admin');
            localStorage.removeItem('username');
          })
        );
      }

      checkSessionStatus(): Observable<SessionStatus> {
        return this.http.get<SessionStatus>(this.sessionStatusUrl).pipe(
          tap(status => {
            this._isAuthenticated.next(status.is_authenticated);
            this._isAdmin.next(status.is_admin || false);
            this._username.next(status.username || null);
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
    