class ProductManager {
    constructor() {
        this.currentProduct = null;
        this.init();
    }

    init() {
        this.attachEventListeners();
        this.loadProducts();
    }

    attachEventListeners() {
        const addBtn = document.getElementById('addProductBtn');
        const saveBtn = document.getElementById('saveProductBtn');
        const cancelBtn = document.getElementById('cancelProductBtn');
        const searchInput = document.getElementById('searchProduct');

        if (addBtn) addBtn.addEventListener('click', () => this.showAddModal());
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveProduct());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.hideModal());
        if (searchInput) searchInput.addEventListener('input', (e) => this.filterProducts(e.target.value));
    }

    async loadProducts(params = {}) {
        try {
            const response = await API.products.getAll(params);
            this.allProducts = response.data;
            this.renderProducts(response.data);
        } catch (error) {
            showNotification('Failed to load products', 'error');
        }
    }

    renderProducts(products) {
        const tbody = document.getElementById('productsTable');
        if (!tbody) return;

        tbody.innerHTML = products.map(product => `
            <tr data-id="${product.id}">
                <td>${escapeHtml(product.product_code)}</td>
                <td>${escapeHtml(product.product_name)}</td>
                <td>${escapeHtml(product.category || '-')}</td>
                <td>${escapeHtml(product.description || '-')}</td>
                <td><span class="status-badge status-${product.is_active ? 'active' : 'inactive'}">${product.is_active ? 'Active' : 'Inactive'}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" data-action="edit" data-id="${product.id}">Edit</button>
                    <button class="btn btn-sm btn-info" data-action="bom" data-id="${product.id}">BOM</button>
                </td>
            </tr>
        `).join('');

        tbody.querySelectorAll('[data-action]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const id = parseInt(e.target.dataset.id);
                this.handleAction(action, id);
            });
        });
    }

    filterProducts(searchTerm) {
        if (!this.allProducts) return;
        
        const filtered = this.allProducts.filter(product => 
            product.product_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
            product.product_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (product.category && product.category.toLowerCase().includes(searchTerm.toLowerCase()))
        );
        
        this.renderProducts(filtered);
    }

    async handleAction(action, id) {
        if (action === 'edit') {
            await this.editProduct(id);
        } else if (action === 'bom') {
            window.location.href = `/finance/bom?product_id=${id}`;
        }
    }

    showAddModal() {
        this.currentProduct = null;
        document.getElementById('productForm').reset();
        document.getElementById('productModalTitle').textContent = 'Add Product';
        showModal('productModal');
    }

    async editProduct(id) {
        try {
            const response = await API.products.getById(id);
            const product = response.data;
            this.currentProduct = product;

            document.getElementById('productCode').value = product.product_code;
            document.getElementById('productName').value = product.product_name;
            document.getElementById('productDescription').value = product.description || '';
            document.getElementById('productCategory').value = product.category || '';
            document.getElementById('productActive').checked = product.is_active;

            document.getElementById('productModalTitle').textContent = 'Edit Product';
            showModal('productModal');
        } catch (error) {
            showNotification('Failed to load product details', 'error');
        }
    }

    async saveProduct() {
        const data = {
            product_code: document.getElementById('productCode').value,
            product_name: document.getElementById('productName').value,
            description: document.getElementById('productDescription').value || null,
            category: document.getElementById('productCategory').value || null,
            is_active: document.getElementById('productActive').checked
        };

        try {
            if (this.currentProduct) {
                await API.products.update(this.currentProduct.id, data);
                showNotification('Product updated successfully', 'success');
            } else {
                await API.products.create(data);
                showNotification('Product created successfully', 'success');
            }
            this.hideModal();
            this.loadProducts();
        } catch (error) {
            showNotification(error.message || 'Failed to save product', 'error');
        }
    }

    hideModal() {
        hideModal('productModal');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new ProductManager());
} else {
    new ProductManager();
}
