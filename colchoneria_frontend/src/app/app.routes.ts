// src/app/app.routes.ts
import { Routes } from '@angular/router';
import { ProductListComponent } from './components/product-list/product-list'
import { ProductUpload } from './components/product-upload/product-upload'; // Asegúrate que la ruta es correcta
import {LoginComponent } from './components/login/login';
import { ProductDetailsComponent } from './components/product-details/product-details';

export const routes: Routes = [
  { path: 'productos', component: ProductListComponent },
  { path: 'subir-excel', component: ProductUpload },
  { path: 'login', component: LoginComponent },
  { path: 'productos/:id', component: ProductDetailsComponent },
  { path: '', redirectTo: '/productos', pathMatch: 'full' },
  { path: '**', redirectTo: '/productos' }
];