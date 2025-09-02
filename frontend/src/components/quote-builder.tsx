// src/components/quote-builder.tsx

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Trash2 } from "lucide-react";

interface QuoteBuilderProps {
  clientId: string;
  conversationId: string;
  onSubmit: (quoteData: any) => void;
}

export function QuoteBuilder({ clientId, conversationId, onSubmit }: QuoteBuilderProps) {
  const [products, setProducts] = useState([
    { id: '1', name: '', description: '', price: 0, quantity: 1 }
  ]);
  const [validUntil, setValidUntil] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() + 15);
    return date.toISOString().split('T')[0];
  });
  const [notes, setNotes] = useState('');

  const addProduct = () => {
    const newId = (products.length + 1).toString();
    setProducts([...products, { 
      id: newId, 
      name: '', 
      description: '', 
      price: 0, 
      quantity: 1 
    }]);
  };

  const removeProduct = (id: string) => {
    setProducts(products.filter(p => p.id !== id));
  };

  const updateProduct = (id: string, field: string, value: any) => {
    setProducts(products.map(p => 
      p.id === id ? { ...p, [field]: value } : p
    ));
  };

  const calculateTotal = () => {
    return products.reduce((sum, product) => 
      sum + (product.price * product.quantity), 0);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const quoteData = {
      conversation_id: conversationId,
      client_id: clientId,
      products: products.filter(p => p.name),
      valid_until: validUntil,
      notes
    };
    
    onSubmit(quoteData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
        {products.map((product, index) => (
          <div key={product.id} className="border rounded-lg p-4 bg-muted/50">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-medium">Produit #{index + 1}</h4>
              {products.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeProduct(product.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor={`name-${product.id}`}>Nom du produit</Label>
                <Input
                  id={`name-${product.id}`}
                  value={product.name}
                  onChange={(e) => updateProduct(product.id, 'name', e.target.value)}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor={`qty-${product.id}`}>Quantité</Label>
                <Input
                  id={`qty-${product.id}`}
                  type="number"
                  min="1"
                  value={product.quantity}
                  onChange={(e) => updateProduct(product.id, 'quantity', parseInt(e.target.value) || 1)}
                  required
                />
              </div>
            </div>
            
            <div className="space-y-2 mt-2">
              <Label htmlFor={`desc-${product.id}`}>Description</Label>
              <Textarea
                id={`desc-${product.id}`}
                value={product.description}
                onChange={(e) => updateProduct(product.id, 'description', e.target.value)}
                rows={2}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4 mt-2">
              <div className="space-y-2">
                <Label htmlFor={`price-${product.id}`}>Prix unitaire (DT)</Label>
                <Input
                  id={`price-${product.id}`}
                  type="number"
                  step="0.01"
                  min="0"
                  value={product.price}
                  onChange={(e) => updateProduct(product.id, 'price', parseFloat(e.target.value) || 0)}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label>Total</Label>
                <div className="flex items-center h-10 px-3 border rounded-md bg-background">
                  {(product.price * product.quantity).toFixed(2)} DT
                </div>
              </div>
            </div>
          </div>
        ))}
        
        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={addProduct}
        >
          <Plus className="h-4 w-4 mr-2" />
          Ajouter un produit
        </Button>
        
        <div className="border-t pt-4">
          <div className="flex justify-between items-center font-bold text-lg mb-4">
            <span>Total général:</span>
            <span>{calculateTotal().toFixed(2)} DT</span>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Date d'expiration</Label>
              <Input
                type="date"
                value={validUntil}
                onChange={(e) => setValidUntil(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Notes supplémentaires</Label>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Informations supplémentaires pour le client..."
              />
            </div>
          </div>
        </div>
      </div>
      
      <div className="flex justify-end space-x-2 pt-4 border-t">
        <Button type="submit" className="bg-bh-navy">
          Créer le devis
        </Button>
      </div>
    </form>
  );
}