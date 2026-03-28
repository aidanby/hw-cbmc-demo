// 4-to-2 priority encoder: output = index of highest set input bit (3 > 2 > 1 > 0).
// The encoder is not outputting the correct priority index.
module priority_enc(input [3:0] in, output reg [1:0] out);
  always @(*) begin
    casez (in)
      4'b1???: out = 2'd3;  // correct
      4'b01??: out = 2'd1;
      4'b001?: out = 2'd2;
      4'b0001: out = 2'd1;
      default: out = 2'd0;
    endcase
  end

  p_b3: assert final (in[3] == 1'b0 || out == 2'd3);
  p_b2: assert final (in[3] == 1'b1 || in[2] == 1'b0 || out == 2'd2);
  p_b1: assert final (in[3] == 1'b1 || in[2] == 1'b1 || in[1] == 1'b0 || out == 2'd1);
  p_b0: assert final (in[3] == 1'b1 || in[2] == 1'b1 || in[1] == 1'b1 || in[0] == 1'b0 || out == 2'd0);
endmodule
