// src/components/quote-card.tsx

import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { File, Send, CheckCircle, XCircle, Download } from "lucide-react";

interface Quote {
  id: string;
  products: {
    name: string;
    description: string;
    price: number;
    quantity: number;
  }[];
  total_amount: number;
  valid_until: string;
  status: string;
  created_at: string;
  notes?: string;
}

interface QuoteCardProps {
  quote: Quote;
  onSend?: () => void;
  onAccept?: () => void;
  onReject?: () => void;
}

export function QuoteCard({ quote, onSend, onAccept, onReject }: QuoteCardProps) {
  const getStatusBadge = () => {
    switch (quote.status) {
      case 'draft':
        return <Badge variant="outline">Brouillon</Badge>;
      case 'sent':
        return <Badge variant="default">Envoyé</Badge>;
      case 'accepted':
        return <Badge variant="default">Accepté</Badge>;
      case 'rejected':
        return <Badge variant="destructive">Rejeté</Badge>;
      case 'expired':
        return <Badge variant="outline">Expiré</Badge>;
      default:
        return <Badge variant="outline">{quote.status}</Badge>;
    }
  };

  return (
    <Card className="mb-4">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">Devis #{quote.id.substring(0, 6)}</CardTitle>
        {getStatusBadge()}
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div>
              <p className="text-muted-foreground">Date</p>
              <p>{new Date(quote.created_at).toLocaleDateString('fr-TN')}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Valable jusqu'au</p>
              <p>{new Date(quote.valid_until).toLocaleDateString('fr-TN')}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Total</p>
              <p className="font-bold">{quote.total_amount.toFixed(2)} DT</p>
            </div>
          </div>
          
          <div className="border rounded-md overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left p-2">Produit</th>
                  <th className="text-left p-2">Description</th>
                  <th className="text-right p-2">Qté</th>
                  <th className="text-right p-2">Prix</th>
                </tr>
              </thead>
              <tbody>
                {quote.products.map((product, index) => (
                  <tr key={index} className={index % 2 === 0 ? "bg-muted/50" : ""}>
                    <td className="p-2">{product.name}</td>
                    <td className="p-2">{product.description}</td>
                    <td className="text-right p-2">{product.quantity}</td>
                    <td className="text-right p-2">{product.price.toFixed(2)} DT</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {quote.notes && (
            <div className="mt-2 p-2 bg-muted rounded-md">
              <p className="text-sm">{quote.notes}</p>
            </div>
          )}
        </div>
      </CardContent>
      <CardFooter className="flex justify-between">
        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Télécharger
        </Button>
        
        {quote.status === 'draft' && onSend && (
          <Button size="sm" onClick={onSend}>
            <Send className="h-4 w-4 mr-2" />
            Envoyer
          </Button>
        )}
        
        {quote.status === 'sent' && (
          <div className="flex space-x-2">
            {onAccept && (
              <Button variant="default" size="sm" onClick={onAccept}>
                <CheckCircle className="h-4 w-4 mr-2" />
                Accepter
              </Button>
            )}
            {onReject && (
              <Button variant="destructive" size="sm" onClick={onReject}>
                <XCircle className="h-4 w-4 mr-2" />
                Rejeter
              </Button>
            )}
          </div>
        )}
      </CardFooter>
    </Card>
  );
}