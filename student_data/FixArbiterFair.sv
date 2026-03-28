// 2-client round-robin arbiter.
// The arbiter is not distributing grants correctly between clients.
module arbiter_fair(input clk, input reset,
                    input req0, req1,
                    output reg grant0, output reg grant1);
  reg turn;  // 0 = client 0's turn, 1 = client 1's turn
  initial begin
    grant0 = 0;
    grant1 = 0;
    turn   = 0;
  end

  always @(posedge clk) begin
    if (reset) begin
      grant0 <= 0;
      grant1 <= 0;
      turn   <= 0;
    end else begin
      grant0 <= 0;
      grant1 <= 0;
      if (req0 && (!req1 || turn == 1)) begin
        grant0 <= 1;
        turn   <= 0;                         
      end else if (req1) begin
        grant1 <= 1;
        turn   <= 1;                         
      end
    end
  end

  p_mutex:     assert property (@(posedge clk) !(grant0 && grant1));
  p_req0_only: assert property (@(posedge clk) req0 && !req1 && !reset |=> grant0);
  p_req1_only: assert property (@(posedge clk) !req0 && req1 && !reset |=> grant1);
  p_fair0:     assert property (@(posedge clk) req0 && req1 && !reset && turn == 0 |=> grant0);
  p_turn_g0:   assert property (@(posedge clk) grant0 && !reset |-> turn == 1);
  p_turn_g1:   assert property (@(posedge clk) grant1 && !reset |-> turn == 0);
endmodule
