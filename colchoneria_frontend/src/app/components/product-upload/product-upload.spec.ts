import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ProductUpload } from './product-upload';

describe('ProductUpload', () => {
  let component: ProductUpload;
  let fixture: ComponentFixture<ProductUpload>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductUpload]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ProductUpload);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
