// 4-bit ripple carry adder.
// BUG: carry uses & instead of | in the sum-of-products carry logic.
// Fix the carry computation so all properties pass.
module adder_carry(input [3:0] a, b, output [3:0] sum, output carry);
  // Explicit carry computation using sum-of-products (carry generate/propagate)
  wire g0, g1, g2, g3;  // generate: a[i] & b[i]
  wire p0, p1, p2, p3;  // propagate: a[i] ^ b[i]
  wire c0, c1, c2;      // internal carry bits

  assign g0 = a[0] & b[0];
  assign g1 = a[1] & b[1];
  assign g2 = a[2] & b[2];
  assign g3 = a[3] & b[3];

  assign p0 = a[0] ^ b[0];
  assign p1 = a[1] ^ b[1];
  assign p2 = a[2] ^ b[2];
  assign p3 = a[3] ^ b[3];

  // BUG: c0 uses & instead of | (carry lookahead: c0 = g0)
  assign c0 = g0;
  assign c1 = g1 & (p1 & c0);  // BUG: should be g1 | (p1 & c0)
  assign c2 = g2 & (p2 & c1);  // BUG: should be g2 | (p2 & c1)
  assign carry = g3 & (p3 & c2); // BUG: should be g3 | (p3 & c2)

  assign sum[0] = p0;
  assign sum[1] = p1 ^ c0;
  assign sum[2] = p2 ^ c1;
  assign sum[3] = p3 ^ c2;

  p_sum:   assert final (sum == (a + b) % 16);
  p_carry: assert final (carry == ((a + b) >= 16 ? 1'b1 : 1'b0));
endmodule
