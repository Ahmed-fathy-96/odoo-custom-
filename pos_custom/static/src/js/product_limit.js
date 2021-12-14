odoo.define('pos_custom.product_limit', function (require) {
    'use strict';
    var ProductScreen = require('point_of_sale.ProductScreen');
    var Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    var ProductScreenLimit = ProductScreen =>
    class extends ProductScreen {

        async _clickProduct(event){

            if (!this.currentOrder) {
                this.env.pos.add_new_order();
            }
            const product = event.detail;
            let price_extra = 0.0;
            let draftPackLotLines, weight, description, packLotLinesToEdit;
            let check_product = this.currentOrder.get_orderlines();

            if(check_product.length){
               if(check_product.find(line => line.product.id === product.id)){
                let qty = check_product.find(line => line.product.id === product.id).quantity + 1
                if ( qty > 3){
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Quantity Limit'),
                        body: 'Sorry you can not add more than 3',
                    });
                    return;
                }
            }

            }
            if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                                  .filter((attr) => attr !== undefined);
                let { confirmed, payload } = await this.showPopup('ProductConfiguratorPopup', {
                    product: product,
                    attributes: attributes,
                });

                if (confirmed) {
                    description = payload.selected_attributes.join(', ');
                    price_extra += payload.price_extra;
                } else {
                    return;
                }
            }

            // Gather lot information if required.
            if (['serial', 'lot'].includes(product.tracking)) {
                const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                if (isAllowOnlyOneLot) {
                    packLotLinesToEdit = [];
                } else {
                    const orderline = this.currentOrder
                        .get_orderlines()
                        .filter(line => !line.get_discount())
                        .find(line => line.product.id === product.id);
                    if (orderline) {
                        packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                    } else {
                        packLotLinesToEdit = [];
                    }
                }
                const { confirmed, payload } = await this.showPopup('EditListPopup', {
                    title: this.env._t('Lot/Serial Number(s) Required'),
                    isSingleItem: isAllowOnlyOneLot,
                    array: packLotLinesToEdit,
                });
                if (confirmed) {
                    // Segregate the old and new packlot lines
                    const modifiedPackLotLines = Object.fromEntries(
                        payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                    );
                    const newPackLotLines = payload.newArray
                        .filter(item => !item.id)
                        .map(item => ({ lot_name: item.text }));

                    draftPackLotLines = { modifiedPackLotLines, newPackLotLines };
                } else {
                    // We don't proceed on adding product.
                    return;
                }
            }

            // Take the weight if necessary.
            if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
                // Show the ScaleScreen to weigh the product.
                if (this.isScaleAvailable) {
                    const { confirmed, payload } = await this.showTempScreen('ScaleScreen', {
                        product,
                    });
                    if (confirmed) {
                        weight = payload.weight;
                    } else {
                        // do not add the product;
                        return;
                    }
                } else {
                    await this._onScaleNotAvailable();
                }
            }

            // Add the product after having the extra information.
            this.currentOrder.add_product(product, {
                draftPackLotLines,
                description: description,
                price_extra: price_extra,
                quantity: weight,
            });

            NumberBuffer.reset();

        }

        _setValue(val) {
            if (this.currentOrder.get_selected_orderline()) {
                if (this.state.numpadMode === 'quantity') {
                    let currentQuantity = this.currentOrder.get_selected_orderline().get_quantity();
                    let intVal = parseInt(val)
                    if(Number.isInteger(intVal) && intVal > 3 ){
                        this.showPopup('ErrorPopup', {
                            title: this.env._t('Quantity Limit'),
                            body: `Sorry you can not add more than ${intVal}`,
                        });
                        NumberBuffer.reset();
                    }else{
                        this.currentOrder.get_selected_orderline().set_quantity(val);
                    }

                } else if (this.state.numpadMode === 'discount') {
                    this.currentOrder.get_selected_orderline().set_discount(val);
                } else if (this.state.numpadMode === 'price') {
                    var selected_orderline = this.currentOrder.get_selected_orderline();
                    selected_orderline.price_manually_set = true;
                    selected_orderline.set_unit_price(val);
                }
                if (this.env.pos.config.iface_customer_facing_display) {
                    this.env.pos.send_current_order_to_customer_facing_display();
                }
            }
        }

    };

    Registries.Component.extend(ProductScreen, ProductScreenLimit);

    return ProductScreenLimit;

 });
