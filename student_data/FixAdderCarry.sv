// 4-bit carry-lookahead adder.
// The adder is producing incorrect results for some input combinations.
module adder_carry(input [3:0] a, b, output [3:0] sum, output carry);
  // Carry lookahead uses generate (g) and propagate (p) terms
  wire g0, g1, g2, g3;  // generate
  wire p0, p1, p2, p3;  // propagate
  wire c0, c1, c2;      // carry chain

  assign g0 = a[0] & b[0];
  assign g1 = a[1] | b[1];
  assign g2 = a[2] & b[2];
  assign g3 = a[3] | b[3];

  assign p0 = a[0] ^ b[0];
  assign p1 = a[1] ^ b[1];
  assign p2 = a[2] ^ b[2];
  assign p3 = a[3] ^ b[3];

  assign c0 = g0;
  assign c1 = g1 | (p1 & c0);
  assign c2 = g2 | (p2 & c1);
  assign carry = g3 | (p3 & c2);

  assign sum[0] = p0;
  assign sum[1] = p1 ^ c0;
  assign sum[2] = p2 ^ c1;
  assign sum[3] = p3 ^ c1;

  p_sum_lo: assert final (sum[2:0] == (a[2:0] + b[2:0]));
  p_sum:    assert final (sum == (a + b) % 16);
  p_carry:  assert final (carry == ((a + b) >= 16 ? 1'b1 : 1'b0));
endmodule
